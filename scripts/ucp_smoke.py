#!/usr/bin/env python3
"""End-to-end smoke test for the UCP add-on.

Runs against a throwaway SQLite database, so it neither needs Docker nor
touches the running Fast Livery stack.

    python scripts/ucp_smoke.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

DB_PATH = Path(tempfile.gettempdir()) / f"ucp_smoke_{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{DB_PATH}"
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("INSTAGRAM_SCHEDULER_ENABLED", "false")

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Client, Product  # noqa: E402

HOST = "tienda.smoke"
CSV = (
    "sku,title,price,currency,availability,image_url,url,gtin\n"
    "TEE-01,Camiseta algodon,25.00,USD,in_stock,https://cdn.smoke/tee.jpg,https://shop.smoke/tee,7701234567897\n"
)


def _section(title: str, payload) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> int:
    Base.metadata.create_all(engine)
    api = TestClient(app)

    registered = api.post(
        "/api/auth/register",
        json={
            "agency_name": "Agencia Smoke",
            "name": "Ana",
            "email": "ana@smoke.com",
            "password": "contrasena-segura",
            "accept_terms": True,
            "accept_privacy": True,
        },
    )
    assert registered.status_code == 201, registered.text

    client = api.post(
        "/api/clients",
        json={
            "name": "Tienda Smoke",
            "industry": "",
            "description": "",
            "general_context": "",
            "is_active": True,
        },
    ).json()
    client_id = client["id"]

    imported = api.post(
        f"/api/clients/{client_id}/products/import",
        files={"file": ("products.csv", CSV, "text/csv")},
    )
    assert imported.status_code == 200, imported.text

    with SessionLocal() as db:
        row = db.get(Client, uuid.UUID(client_id))
        assert row is not None
        db.add(
            Product(
                agency_id=row.agency_id,
                client_id=row.id,
                sku="OLD-02",
                title="Reloj usado",
                price=Decimal("10.00"),
                currency="USD",
                availability="in_stock",
                image_url="https://cdn.smoke/old.jpg",
                url="https://shop.smoke/old",
                category="usado",
            )
        )
        db.commit()

    connection = api.post(
        f"/api/clients/{client_id}/ucp", json={"adapter_kind": "portal"}
    )
    assert connection.status_code == 201, connection.text
    api_key = connection.json()["api_key"]
    _section("Conexion UCP", connection.json()["connection"])

    addendum = api.post(
        f"/api/clients/{client_id}/ucp/addendum", json={"version": "1.0"}
    )
    assert addendum.status_code == 200, addendum.text

    synced = api.post(f"/api/clients/{client_id}/ucp/sync")
    assert synced.status_code == 200, synced.text
    _section("Sync de elegibilidad", synced.json())

    products = api.get(f"/api/clients/{client_id}/ucp/products").json()
    _section("Productos", products)

    with SessionLocal() as db:
        row = db.get(Client, uuid.UUID(client_id))
        assert row is not None
        row.portal_domain = HOST
        row.portal_domain_verified = True
        row.portal_enabled = True
        db.commit()

    profile = api.get("/.well-known/ucp", headers={"host": HOST})
    assert profile.status_code == 200, profile.text
    _section("Perfil /.well-known/ucp", profile.json())

    cart = api.post(
        "/ucp/v1/carts",
        headers={"host": HOST, "x-api-key": api_key},
        json={"line_items": [{"item": {"id": "TEE-01"}, "quantity": 2}]},
    )
    assert cart.status_code == 200, cart.text
    _section("Carrito POST /ucp/v1/carts", cart.json())

    print("\nOK: alta, sync, perfil y carrito funcionando.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        engine.dispose()
        DB_PATH.unlink(missing_ok=True)
