"""UCP add-on: connection, eligibility sync, profile and cart handoff."""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient

from conftest import TestingSession
from app.main import app
from app.models import Client, Product

HOST = "tienda.test"


def _client(api: TestClient, name: str = "Demo") -> dict:
    response = api.post(
        "/api/clients",
        json={
            "name": name,
            "industry": "",
            "description": "",
            "general_context": "",
            "is_active": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _seed_products(client_id: str) -> None:
    with TestingSession() as db:
        client = db.get(Client, uuid.UUID(client_id))
        assert client is not None
        db.add_all(
            [
                Product(
                    agency_id=client.agency_id,
                    client_id=client.id,
                    sku="TEE-01",
                    title="Camiseta",
                    price=Decimal("25.00"),
                    currency="USD",
                    availability="in_stock",
                    image_url="https://cdn.test/tee.jpg",
                    url="https://shop.test/tee",
                ),
                Product(
                    agency_id=client.agency_id,
                    client_id=client.id,
                    sku="OLD-02",
                    title="Reloj usado",
                    price=Decimal("10.00"),
                    currency="USD",
                    availability="in_stock",
                    image_url="https://cdn.test/old.jpg",
                    url="https://shop.test/old",
                    category="usado",
                ),
                Product(
                    agency_id=client.agency_id,
                    client_id=client.id,
                    sku="OUT-03",
                    title="Lampara",
                    price=Decimal("30.00"),
                    currency="USD",
                    availability="agotado",
                    image_url="https://cdn.test/lamp.jpg",
                    url="https://shop.test/lamp",
                ),
            ]
        )
        db.commit()


def _verify_domain(client_id: str, host: str = HOST) -> None:
    with TestingSession() as db:
        client = db.get(Client, uuid.UUID(client_id))
        assert client is not None
        client.portal_domain = host
        client.portal_domain_verified = True
        client.portal_enabled = True
        db.commit()


def test_connect_sync_and_eligibility(authenticated_client: TestClient):
    client = _client(authenticated_client)
    _seed_products(client["id"])

    created = authenticated_client.post(
        f"/api/clients/{client['id']}/ucp", json={"adapter_kind": "portal"}
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["api_key"].startswith("ucp_")
    assert body["connection"]["status"] == "draft"

    sync = authenticated_client.post(f"/api/clients/{client['id']}/ucp/sync")
    assert sync.status_code == 200, sync.text
    assert sync.json() == {"synced": 3, "eligible": 1, "ineligible": 2}

    products = authenticated_client.get(f"/api/clients/{client['id']}/ucp/products").json()
    by_sku = {item["sku"]: item for item in products}
    assert by_sku["TEE-01"]["checkout_eligibility"] is True
    assert by_sku["TEE-01"]["publish_status"] == "sent"
    assert by_sku["OLD-02"]["last_error"] == "excluded_category"
    assert by_sku["OUT-03"]["last_error"] == "out_of_stock"

    addendum = authenticated_client.post(
        f"/api/clients/{client['id']}/ucp/addendum", json={"version": "1.0"}
    )
    assert addendum.status_code == 200, addendum.text
    assert addendum.json()["status"] == "pending_review"
    assert addendum.json()["addendum_accepted_at"] is not None


def test_profile_and_cart_handoff(authenticated_client: TestClient):
    client = _client(authenticated_client)
    _seed_products(client["id"])
    created = authenticated_client.post(f"/api/clients/{client['id']}/ucp", json={}).json()
    api_key = created["api_key"]
    _verify_domain(client["id"])

    profile = authenticated_client.get(
        "/.well-known/ucp", headers={"host": HOST}
    )
    assert profile.status_code == 200, profile.text
    body = profile.json()
    assert body["ucp"]["version"] == "2026-04-08"
    assert "dev.ucp.shopping.cart" in body["ucp"]["capabilities"]

    missing_key = authenticated_client.post(
        "/ucp/v1/carts",
        headers={"host": HOST},
        json={"line_items": [{"item": {"id": "TEE-01"}, "quantity": 2}]},
    )
    assert missing_key.status_code == 401

    cart = authenticated_client.post(
        "/ucp/v1/carts",
        headers={"host": HOST, "x-api-key": api_key},
        json={"line_items": [{"item": {"id": "TEE-01"}, "quantity": 2}]},
    )
    assert cart.status_code == 200, cart.text
    payload = cart.json()
    assert payload["id"].startswith("cart_")
    assert payload["currency"] == "USD"
    assert payload["line_items"][0]["totals"][0]["amount"] == 5000
    assert payload["totals"][1]["amount"] == 5000
    assert f"/portal/{client['portal_slug']}" in payload["continue_url"]

    unknown = authenticated_client.post(
        "/ucp/v1/carts",
        headers={"host": HOST, "x-api-key": api_key},
        json={"line_items": [{"item": {"id": "NOPE"}}]},
    )
    assert unknown.status_code == 400
    assert unknown.json()["messages"][0]["code"] == "unknown_item"


def test_tenant_isolation(authenticated_client: TestClient):
    client = _client(authenticated_client, "Privado")
    authenticated_client.post(f"/api/clients/{client['id']}/ucp", json={})

    other = TestClient(app)
    registered = other.post(
        "/api/auth/register",
        json={
            "agency_name": "Agencia Otra",
            "name": "Beto",
            "email": "beto@otra.com",
            "password": "contrasena-segura",
            "accept_terms": True,
            "accept_privacy": True,
        },
    )
    assert registered.status_code == 201, registered.text
    assert other.get(f"/api/clients/{client['id']}/ucp").status_code == 404
