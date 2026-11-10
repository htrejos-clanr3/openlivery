"""UCP service: eligibility, profile, cart handoff and Merchant Center publishing.

The Merchant API push is intentionally isolated: until the OAuth connection to
Merchant Center exists, products are validated and marked "eligible" locally.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Client, Product, now_utc
from ..models_ucp import UcpCartSession, UcpConnection, UcpEvent, UcpProduct

UCP_VERSION = "2026-04-08"
CART_CAPABILITY = "dev.ucp.shopping.cart"
CART_SPEC = "https://ucp.dev/2026-04-08/specification/cart"
CART_SCHEMA = "https://ucp.dev/2026-04-08/schemas/shopping/cart.json"
SHOPPING_SPEC = "https://ucp.dev/2026-04-08/specification/overview"
SHOPPING_SCHEMA = "https://ucp.dev/2026-04-08/services/shopping/rest.openapi.json"

# Categories Google excludes from UCP checkout (see Merchant Center guide).
EXCLUDED_CATEGORY_KEYWORDS = (
    "suscripci", "subscription", "financiaci", "installment",
    "personaliz", "custom", "usado", "used", "refurbish", "reacondicion",
    "preventa", "pre-order", "preorder", "alquiler", "rental",
    "servicio", "service", "digital", "curso", "course",
    "arma", "weapon", "adulto", "adult", "farmacia", "pharmacy",
    "alcohol", "tabaco", "tobacco", "apuesta", "gambling",
)
OUT_OF_STOCK = {"agotado", "out_of_stock", "outofstock", "sin_stock", "sold_out", "sold out"}


def new_api_key() -> tuple[str, str]:
    """Return (raw key, hash). The raw key is shown once and never stored."""
    raw = f"ucp_{secrets.token_urlsafe(32)}"
    return raw, hash_api_key(raw)


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def api_key_matches(raw: str, stored_hash: str) -> bool:
    return bool(raw) and bool(stored_hash) and secrets.compare_digest(hash_api_key(raw), stored_hash)


def validate_product(product: Product) -> list[str]:
    """Return blocking issues. An empty list means the product is eligible."""
    issues: list[str] = []
    if not (product.title or "").strip():
        issues.append("missing_title")
    if product.price is None or product.price <= 0:
        issues.append("invalid_price")
    if not (product.currency or "").strip():
        issues.append("missing_currency")
    if not (product.image_url or "").strip().startswith("https://"):
        issues.append("invalid_image")
    if not (product.url or "").strip():
        issues.append("missing_url")
    if (product.availability or "").strip().lower() in OUT_OF_STOCK:
        issues.append("out_of_stock")
    category = f"{product.category or ''} {product.title or ''}".lower()
    if any(keyword in category for keyword in EXCLUDED_CATEGORY_KEYWORDS):
        issues.append("excluded_category")
    return issues


def build_profile(connection: UcpConnection, base_url: str) -> dict:
    """Business profile served at /.well-known/ucp."""
    endpoint = f"{base_url.rstrip('/')}/ucp/v1"
    return {
        "ucp": {
            "version": UCP_VERSION,
            "services": {
                "dev.ucp.shopping": [
                    {
                        "version": UCP_VERSION,
                        "spec": SHOPPING_SPEC,
                        "transport": "rest",
                        "endpoint": endpoint,
                        "schema": SHOPPING_SCHEMA,
                    }
                ]
            },
            "capabilities": {
                CART_CAPABILITY: [
                    {
                        "version": UCP_VERSION,
                        "spec": CART_SPEC,
                        "schema": CART_SCHEMA,
                    }
                ]
            },
        }
    }


def sync_connection(db: Session, connection: UcpConnection, client: Client) -> dict:
    """Recompute eligibility for the client catalog and update publish state."""
    settings = get_settings()
    mock = getattr(settings, "ucp_mock_mode", True)
    now = now_utc()

    products = db.scalars(select(Product).where(Product.client_id == client.id)).all()
    rows = {
        row.product_id: row
        for row in db.scalars(
            select(UcpProduct).where(UcpProduct.connection_id == connection.id)
        ).all()
    }

    eligible = 0
    for product in products:
        issues = validate_product(product)
        ok = not issues
        row = rows.get(product.id)
        if row is None:
            row = UcpProduct(connection_id=connection.id, product_id=product.id)
            db.add(row)
        row.merchant_item_id = product.sku
        row.checkout_eligibility = ok
        row.last_error = "; ".join(issues)
        if ok:
            eligible += 1
            row.publish_status = "sent" if mock else "eligible"
        else:
            row.publish_status = "ineligible"
        row.synced_at = now

    connection.last_sync_at = now
    connection.last_error = ""
    if connection.addendum_accepted_at and connection.status == "draft":
        connection.status = "pending_review"
    db.add(
        UcpEvent(
            connection_id=connection.id,
            kind="sync",
            request={"products": len(products)},
            response={"eligible": eligible, "ineligible": len(products) - eligible},
            status_code=200,
            created_at=now,
        )
    )
    return {
        "synced": len(products),
        "eligible": eligible,
        "ineligible": len(products) - eligible,
    }


def continue_url(connection: UcpConnection, client: Client, cart_id: uuid.UUID, base_url: str) -> str:
    if connection.adapter_kind == "store" and connection.store_base_url:
        return f"{connection.store_base_url.rstrip('/')}/cart?ucp_cart={cart_id}"
    return f"{base_url.rstrip('/')}/portal/{client.portal_slug}?ucp_cart={cart_id}"


def cart_error(code: str, content: str) -> dict:
    return {
        "ucp": {"version": UCP_VERSION, "status": "error"},
        "messages": [
            {
                "type": "error",
                "code": code,
                "content": content,
                "severity": "unrecoverable",
            }
        ],
    }


def create_cart(
    db: Session,
    connection: UcpConnection,
    client: Client,
    lines: list[dict],
    base_url: str,
) -> tuple[dict | None, str | None]:
    """Build the cart response for POST /carts. Returns (payload, error_code)."""
    if not lines:
        return None, "empty_cart"

    quantities: dict[str, int] = {}
    for line in lines:
        item_id = (line.get("id") or "").strip()
        if not item_id:
            return None, "invalid_line_item"
        try:
            quantity = int(line.get("quantity") or 1)
        except (TypeError, ValueError):
            return None, "invalid_quantity"
        quantities[item_id] = quantities.get(item_id, 0) + max(1, quantity)

    products = {
        product.sku: product
        for product in db.scalars(
            select(Product).where(
                Product.client_id == client.id,
                Product.sku.in_(list(quantities)),
            )
        ).all()
    }
    if any(sku not in products for sku in quantities):
        return None, "unknown_item"

    currency = ""
    cart_lines = []
    subtotal = 0
    for sku, quantity in quantities.items():
        product = products[sku]
        if product.price is None:
            return None, "missing_price"
        if currency and product.currency and product.currency != currency:
            return None, "currency_mismatch"
        currency = currency or product.currency
        amount = int(product.price * 100) * quantity
        subtotal += amount
        cart_lines.append(
            {
                "id": f"li_{sku}",
                "item": {"id": sku, "title": product.title, "price": int(product.price * 100)},
                "quantity": quantity,
                "totals": [
                    {"type": "subtotal", "amount": amount},
                    {"type": "total", "amount": amount},
                ],
            }
        )

    now = now_utc()
    session = UcpCartSession(
        connection_id=connection.id,
        status="open",
        payload={"line_items": cart_lines, "currency": currency},
        continue_url="",
        expires_at=now + timedelta(hours=1),
        created_at=now,
    )
    db.add(session)
    db.flush()

    url = continue_url(connection, client, session.id, base_url)
    session.continue_url = url

    response = {
        "ucp": {
            "version": UCP_VERSION,
            "capabilities": {CART_CAPABILITY: [{"version": UCP_VERSION}]},
        },
        "id": f"cart_{session.id.hex}",
        "line_items": cart_lines,
        "currency": currency,
        "totals": [
            {"type": "subtotal", "amount": subtotal},
            {
                "type": "total",
                "amount": subtotal,
                "display_text": "Estimated total (taxes calculated at checkout)",
            },
        ],
        "continue_url": url,
        "expires_at": session.expires_at.isoformat().replace("+00:00", "Z"),
    }
    db.add(
        UcpEvent(
            connection_id=connection.id,
            kind="cart.create",
            request={"line_items": [{"id": k, "quantity": v} for k, v in quantities.items()]},
            response={"cart_id": str(session.id), "currency": currency},
            status_code=200,
            created_at=now,
        )
    )
    return response, None
