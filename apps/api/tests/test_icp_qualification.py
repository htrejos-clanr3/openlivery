"""Ideal customer profile and deterministic lead qualification."""

from __future__ import annotations

from fastapi.testclient import TestClient

CLIENT_BODY = {"industry": "", "description": "", "general_context": "", "is_active": True}
ICP_BODY = {
    "sectors": ["inmobiliaria"],
    "cities": ["bogota"],
    "keywords": ["apartamentos", "arriendo"],
    "disqualifiers": ["gratis"],
    "size_min": None,
    "size_max": None,
    "hot_min": 70,
    "warm_min": 40,
    "auto_qualify": False,
}


def _client(api: TestClient, name: str = "Acme") -> dict:
    response = api.post("/api/clients", json={**CLIENT_BODY, "name": name})
    assert response.status_code == 201, response.text
    return response.json()


def _icp(api: TestClient, client_id: str, **overrides) -> dict:
    body = {**ICP_BODY, **overrides}
    response = api.put(f"/api/clients/{client_id}/leads/icp", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _lead(api: TestClient, client_id: str, **overrides) -> dict:
    body = {
        "name": "Luis Perez",
        "email": "luis@acme.com",
        "phone": "+57 300 111 2233",
        "company": "Inmobiliaria Horizonte",
        "notes": "Busca apartamentos en Bogota para arriendo",
        **overrides,
    }
    response = api.post(f"/api/clients/{client_id}/leads", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_icp_upsert_read_and_validation(authenticated_client: TestClient):
    client = _client(authenticated_client)
    missing = authenticated_client.get(f"/api/clients/{client['id']}/leads/icp")
    assert missing.status_code == 404

    created = _icp(authenticated_client, client["id"])
    assert created["sectors"] == ["inmobiliaria"]
    assert created["hot_min"] == 70

    fetched = authenticated_client.get(f"/api/clients/{client['id']}/leads/icp")
    assert fetched.status_code == 200
    assert fetched.json()["cities"] == ["bogota"]

    invalid = authenticated_client.put(
        f"/api/clients/{client['id']}/leads/icp",
        json={**ICP_BODY, "hot_min": 30, "warm_min": 40},
    )
    assert invalid.status_code == 422

    bad_size = authenticated_client.put(
        f"/api/clients/{client['id']}/leads/icp",
        json={**ICP_BODY, "size_min": 500, "size_max": 10},
    )
    assert bad_size.status_code == 422


def test_icp_is_agency_scoped(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={
            "agency_name": "Primera",
            "name": "Ana",
            "email": "ana-icp@prisma.com",
            "password": "contrasena-segura",
            "accept_terms": True,
            "accept_privacy": True,
        },
    )
    assert response.status_code == 201, response.text
    owner_client = _client(client, "Duena")
    _icp(client, owner_client["id"])

    other = client.post(
        "/api/auth/register",
        json={
            "agency_name": "Otra",
            "name": "Beto",
            "email": "beto-icp@prisma.com",
            "password": "contrasena-segura",
            "accept_terms": True,
            "accept_privacy": True,
        },
    )
    assert other.status_code == 201, other.text

    assert client.get(f"/api/clients/{owner_client['id']}/leads/icp").status_code == 404
    assert client.put(f"/api/clients/{owner_client['id']}/leads/icp", json=ICP_BODY).status_code == 404


def test_qualify_lead_scores_and_records_activity(authenticated_client: TestClient):
    client = _client(authenticated_client)
    _icp(authenticated_client, client["id"])
    lead = _lead(authenticated_client, client["id"])

    response = authenticated_client.post(f"/api/clients/{client['id']}/leads/{lead['id']}/qualify")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["score"] >= 70
    assert body["band"] == "hot"
    assert body["lead"]["score"] == body["score"]
    kinds = [item["kind"] for item in body["lead"]["activities"]]
    assert "qualification" in kinds

    listed = authenticated_client.get(f"/api/clients/{client['id']}/leads").json()
    assert listed[0]["score"] == body["score"]


def test_disqualifier_zeroes_the_score(authenticated_client: TestClient):
    client = _client(authenticated_client)
    _icp(authenticated_client, client["id"])
    lead = _lead(authenticated_client, client["id"], notes="Quiere todo gratis")

    body = authenticated_client.post(
        f"/api/clients/{client['id']}/leads/{lead['id']}/qualify"
    ).json()
    assert body["score"] == 0
    assert body["band"] == "disqualified"


def test_qualify_without_profile_returns_400(authenticated_client: TestClient):
    client = _client(authenticated_client)
    lead = _lead(authenticated_client, client["id"])
    response = authenticated_client.post(f"/api/clients/{client['id']}/leads/{lead['id']}/qualify")
    assert response.status_code == 400
    assert authenticated_client.post(f"/api/clients/{client['id']}/leads/qualify").status_code == 400


def test_bulk_qualify_covers_every_lead(authenticated_client: TestClient):
    client = _client(authenticated_client)
    _icp(authenticated_client, client["id"])
    _lead(authenticated_client, client["id"])
    _lead(authenticated_client, client["id"], name="Otra Persona", email="otra@acme.com")

    response = authenticated_client.post(f"/api/clients/{client['id']}/leads/qualify")
    assert response.status_code == 200, response.text
    assert response.json()["qualified"] == 2

    listed = authenticated_client.get(f"/api/clients/{client['id']}/leads").json()
    assert all(lead["score"] is not None for lead in listed)


def test_auto_qualify_on_manual_create(authenticated_client: TestClient):
    client = _client(authenticated_client)
    _icp(authenticated_client, client["id"], auto_qualify=True)

    lead = _lead(authenticated_client, client["id"])
    assert lead["score"] is not None
    detail = authenticated_client.get(f"/api/clients/{client['id']}/leads/{lead['id']}").json()
    assert any(item["kind"] == "qualification" for item in detail["activities"])


def test_csv_import_creates_skips_and_reports(authenticated_client: TestClient):
    client = _client(authenticated_client)
    _icp(authenticated_client, client["id"])
    _lead(authenticated_client, client["id"])

    csv_body = (
        "name,email,phone,company,sector,city,tags,notes,source\n"
        "Ana Gomez,ana@acme.com,+57 300 999 8877,Constructora Loma,constructora,Medellin,web;prospeccion,Llamar manana,form\n"
        "Luis Perez,luis@acme.com,+57 300 111 2233,Inmobiliaria Horizonte,inmobiliaria,Bogota,,Duplicado,form\n"
        ",,,,Bogota,,Sin datos de contacto,form\n"
    )
    response = authenticated_client.post(
        f"/api/clients/{client['id']}/leads/import",
        files={"file": ("leads.csv", csv_body, "text/csv")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created"] == 1
    assert body["skipped"] == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row"] == 4

    listed = authenticated_client.get(f"/api/clients/{client['id']}/leads").json()
    imported = next(item for item in listed if item["contact"]["email"] == "ana@acme.com")
    assert imported["contact"]["company"] == "Constructora Loma"
    assert "prospeccion" in imported["tags"]


def test_csv_import_rejects_missing_columns(authenticated_client: TestClient):
    client = _client(authenticated_client)
    response = authenticated_client.post(
        f"/api/clients/{client['id']}/leads/import",
        files={"file": ("leads.csv", "foo,bar\n1,2\n", "text/csv")},
    )
    assert response.status_code == 400
