"""Product catalog: validation, import, listing and tenant isolation."""

from __future__ import annotations

from fastapi.testclient import TestClient

CSV = (
    "sku,title,price,currency,availability,image_url,url,gtin\n"
    "LOMA-01,Silla Loma,890000,COP,en_stock,https://cdn.test/loma.jpg,https://shop.test/loma,7701234567897\n"
    "LAMP-12,Lampara Horizonte,320000,COP,agotado,https://cdn.test/lamp.jpg,https://shop.test/lamp,\n"
    "NEXO-03,Mesa Nexo,410000,COP,in_stock,http://cdn.test/nexo.jpg,https://shop.test/nexo,\n"
    "LOMA-01,Silla duplicada,890000,COP,in_stock,https://cdn.test/dup.jpg,https://shop.test/dup,\n"
)


def _client(api: TestClient, name: str = "Demo") -> dict:
    response = api.post(
        "/api/clients",
        json={"name": name, "industry": "", "description": "", "general_context": "", "is_active": True},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_validate_then_import(authenticated_client: TestClient):
    client = _client(authenticated_client)
    url = f"/api/clients/{client['id']}/products"

    dry = authenticated_client.post(
        f"{url}/validate", files={"file": ("products.csv", CSV, "text/csv")}
    )
    assert dry.status_code == 200, dry.text
    body = dry.json()
    assert body["created"] == 0
    assert body["valid"] == 1
    assert body["warning"] == 1
    assert body["error"] == 2
    assert authenticated_client.get(url).json() == []

    imported = authenticated_client.post(
        f"{url}/import", files={"file": ("products.csv", CSV, "text/csv")}
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["created"] == 2

    products = authenticated_client.get(url).json()
    assert len(products) == 2
    by_sku = {item["sku"]: item for item in products}
    assert by_sku["LOMA-01"]["status"] == "valid"
    assert by_sku["LAMP-12"]["status"] == "warning"
    assert any("GTIN" in message["message"] for message in by_sku["LAMP-12"]["messages"])


def test_import_rejects_file_without_identity_columns(authenticated_client: TestClient):
    client = _client(authenticated_client)
    response = authenticated_client.post(
        f"/api/clients/{client['id']}/products/import",
        files={"file": ("x.csv", "foo,bar\n1,2\n", "text/csv")},
    )
    assert response.status_code == 400


def test_catalog_is_agency_scoped(client: TestClient):
    first = client.post(
        "/api/auth/register",
        json={
            "agency_name": "Uno",
            "name": "Ana",
            "email": "ana-cat@prisma.com",
            "password": "contrasena-segura",
            "accept_terms": True,
            "accept_privacy": True,
        },
    )
    assert first.status_code == 201, first.text
    owner = _client(client, "Dueno")
    client.post(
        f"/api/clients/{owner['id']}/products/import",
        files={"file": ("p.csv", CSV, "text/csv")},
    )

    client.post(
        "/api/auth/register",
        json={
            "agency_name": "Dos",
            "name": "Beto",
            "email": "beto-cat@prisma.com",
            "password": "contrasena-segura",
            "accept_terms": True,
            "accept_privacy": True,
        },
    )
    assert client.get(f"/api/clients/{owner['id']}/products").status_code == 404
