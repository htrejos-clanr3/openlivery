"""Canonical product catalog: normalization and validation.

Validation never blocks an import. Every row is stored with its own status and
messages so a client can fix and re-import only the failures.
"""

from __future__ import annotations

import re
import uuid
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Product, now_utc

AVAILABILITY = ("in_stock", "out_of_stock", "preorder", "backorder")
ALIASES = {
    "sku": {"sku", "item", "id", "codigo", "código", "reference", "referencia"},
    "title": {"title", "name", "nombre", "titulo", "título", "producto"},
    "description": {"description", "descripcion", "descripción", "detalle"},
    "price": {"price", "precio", "valor"},
    "currency": {"currency", "moneda"},
    "availability": {"availability", "disponibilidad", "existencia", "stock"},
    "image_url": {"image_url", "imagen", "image", "foto", "image_link"},
    "url": {"url", "link", "enlace"},
    "gtin": {"gtin", "ean", "upc", "barcode", "codigo_barras"},
    "brand": {"brand", "marca"},
    "category": {"category", "categoria", "categoría", "rubro"},
}
STATUS_ORDER = {"valid": 0, "warning": 1, "error": 2}


def normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def map_headers(headers: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for header in headers:
        key = normalize_text(header).lower()
        for field, aliases in ALIASES.items():
            if (key in aliases or key.replace(" ", "_") in aliases) and field not in mapping:
                mapping[field] = header
                break
    return mapping


def gtin_check(raw: str) -> tuple[bool, str]:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) not in (8, 12, 13, 14):
        return False, "GTIN must have 8, 12, 13 or 14 digits"
    body, check = digits[:-1], int(digits[-1])
    total = 0
    for index, char in enumerate(reversed(body)):
        total += int(char) * (3 if index % 2 == 0 else 1)
    expected = (10 - total % 10) % 10
    if expected != check:
        return False, f"GTIN check digit should be {expected}"
    return True, ""


def parse_price(raw: str) -> Decimal | None:
    text = re.sub(r"[^\d.,-]", "", str(raw or ""))
    if not text:
        return None
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def validate_row(row: dict, *, currency_default: str = "COP") -> tuple[dict, list[dict]]:
    values = {field: normalize_text(row.get(field)) for field in ALIASES}
    messages: list[dict] = []

    def add(level: str, field: str, text: str) -> None:
        messages.append({"level": level, "field": field, "message": text})

    sku = values["sku"] or ""
    if not sku:
        generated = f"{values['title'].lower().replace(' ', '-')[:60] or 'producto'}-" + uuid.uuid4().hex[:6]
        values["sku"] = generated
        add("warning", "sku", f"SKU generado: {generated}")

    if not values["title"]:
        add("error", "title", "Title is required")
    elif len(values["title"]) > 150:
        add("warning", "title", "Title over 150 characters")

    price = parse_price(values["price"])
    if price is None or price <= 0:
        add("error", "price", "Price is missing or not a positive number")
    currency = (values["currency"] or currency_default).upper()[:3]
    if len(currency) != 3:
        add("error", "currency", "Currency must be a 3-letter ISO code")

    availability = values["availability"].lower().replace(" ", "_") or "in_stock"
    availability = {"en_stock": "in_stock", "agotado": "out_of_stock", "preventa": "preorder"}.get(
        availability, availability
    )
    if availability not in AVAILABILITY:
        add("warning", "availability", f"Unknown availability '{availability}', stored as in_stock")
        availability = "in_stock"

    image = values["image_url"]
    if not image:
        add("error", "image_url", "Image is required")
    elif not image.startswith("https://"):
        add("error", "image_url", "Image URL must use HTTPS")

    if not values["url"]:
        add("warning", "url", "Product URL is missing")
    elif not values["url"].startswith("https://"):
        add("error", "url", "Product URL must use HTTPS")

    gtin = re.sub(r"\D", "", values["gtin"]) if values["gtin"] else ""
    if gtin:
        ok, reason = gtin_check(gtin)
        if not ok:
            add("warning", "gtin", reason)
    else:
        add("warning", "gtin", "No GTIN: usable in carousels and chats, not ready for Google")

    status = "error" if any(m["level"] == "error" for m in messages) else "warning" if any(
        m["level"] == "warning" for m in messages
    ) else "valid"

    normalized = {
        "sku": values["sku"][:120],
        "title": values["title"][:200],
        "description": values["description"],
        "price": price,
        "currency": currency,
        "availability": availability,
        "image_url": image[:600],
        "url": values["url"][:600],
        "gtin": gtin or None,
        "brand": values["brand"][:120],
        "category": values["category"][:160],
        "status": status,
        "messages": messages,
    }
    return normalized, messages


def import_rows(
    db: Session,
    *,
    agency_id: uuid.UUID,
    client_id: uuid.UUID,
    rows: list[dict],
    source: str = "file",
    dry_run: bool = False,
) -> dict:
    existing = {
        product.sku
        for product in db.scalars(select(Product).where(Product.client_id == client_id)).all()
    }
    summary = {"created": 0, "updated": 0, "valid": 0, "warning": 0, "error": 0, "rows": []}
    for index, row in enumerate(rows, start=2):
        normalized, messages = validate_row(row)
        sku = normalized["sku"]
        if sku in existing:
            messages.append({"level": "error", "field": "sku", "message": "Duplicate SKU"})
            normalized["status"] = "error"
            normalized["messages"] = messages
        elif normalized["status"] != "error":
            existing.add(sku)
        summary[normalized["status"]] += 1
        summary["rows"].append({"row": index, "sku": sku, "status": normalized["status"], "messages": messages})
        if dry_run or normalized["status"] == "error":
            continue
        product = db.scalar(select(Product).where(Product.client_id == client_id, Product.sku == sku))
        if product is None:
            product = Product(agency_id=agency_id, client_id=client_id, sku=sku, source=source)
            db.add(product)
            summary["created"] += 1
        else:
            summary["updated"] += 1
        for key, value in normalized.items():
            setattr(product, key, value)
        product.raw = row
        product.updated_at = now_utc()
    if not dry_run:
        db.commit()
    return summary
