"""Per-client lead capture: isolation, dedupe, form ingest, WhatsApp hook, retry."""

from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.routers import whatsapp_cloud_webhook as webhook_router
from app.services import ai as ai_service
from app.services import whatsapp_inbound as whatsapp_inbound_service
from app.services.lead_detection import LeadDetectionService
from app.services.lead_capture import normalize_email, normalize_phone, phone_from_chat_id
from tests.test_whatsapp_cloud import _post_signed, _setup_channel, _webhook_payload


def test_normalize_phone_and_email():
    assert normalize_phone("+57 300 111 2233") == "573001112233"
    assert normalize_phone("123") is None
    assert normalize_email(" Ana@Acme.com ") == "ana@acme.com"
    assert normalize_email("not-an-email") is None
    assert phone_from_chat_id("5730011@s.whatsapp.net") == "5730011"


def test_settings_default_off_and_scoped(authenticated_client: TestClient):
    client = authenticated_client.post(
        "/api/clients",
        json={"name": "La Casona", "industry": "", "description": "", "general_context": "", "is_active": True},
    ).json()
    settings = authenticated_client.get(f"/api/clients/{client['id']}/lead-capture")
    assert settings.status_code == 200, settings.text
    body = settings.json()
    assert body["enabled"] is False
    assert "whatsapp" in body["sources"]
    assert body["pipeline"]["stages"]
    assert body["ingest_token"]


def test_form_ingest_creates_lead_and_dedupes(authenticated_client: TestClient):
    client = authenticated_client.post(
        "/api/clients",
        json={"name": "Bistro", "industry": "", "description": "", "general_context": "", "is_active": True},
    ).json()
    settings = authenticated_client.put(
        f"/api/clients/{client['id']}/lead-capture",
        json={"enabled": True, "sources": ["form", "webhook"], "auto_tags": ["web"], "notify_on_new_lead": True},
    )
    assert settings.status_code == 200, settings.text
    token = settings.json()["ingest_token"]

    created = authenticated_client.post(
        f"/api/public/lead-capture/{token}",
        json={"source": "form", "name": "Luis Pérez", "email": "luis@acme.com", "phone": "+57 300 111 2233"},
    )
    assert created.status_code == 201, created.text
    lead_id = created.json()["lead_id"]
    assert lead_id

    again = authenticated_client.post(
        f"/api/public/lead-capture/{token}",
        json={"source": "form", "name": "Luis", "email": "luis@acme.com", "phone": "573001112233"},
    )
    assert again.status_code == 201, again.text
    assert again.json()["lead_id"] == lead_id

    listed = authenticated_client.get(f"/api/clients/{client['id']}/leads")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    row = listed.json()[0]
    assert row["contact"]["email"] == "luis@acme.com"
    assert row["contact"]["phone"] == "573001112233"
    assert "web" in row["tags"]
    assert row["stage_name"] == "Nuevo"

    notes = authenticated_client.get("/api/leads/notifications")
    assert notes.status_code == 200
    assert len(notes.json()) == 1


def test_ingest_unknown_token(authenticated_client: TestClient):
    response = authenticated_client.post(
        "/api/public/lead-capture/not-a-real-token",
        json={"source": "form", "name": "X"},
    )
    assert response.status_code == 404


def test_tenant_isolation(authenticated_client: TestClient, client: TestClient):
    first = authenticated_client.post(
        "/api/clients",
        json={"name": "Uno", "industry": "", "description": "", "general_context": "", "is_active": True},
    ).json()
    settings = authenticated_client.put(
        f"/api/clients/{first['id']}/lead-capture",
        json={"enabled": True, "sources": ["form"]},
    ).json()
    authenticated_client.post(
        f"/api/public/lead-capture/{settings['ingest_token']}",
        json={"source": "form", "name": "Ana", "email": "ana@uno.com"},
    )
    lead_id = authenticated_client.get(f"/api/clients/{first['id']}/leads").json()[0]["id"]

    authenticated_client.post("/api/auth/logout")
    other = client.post(
        "/api/auth/register",
        json={
            "agency_name": "Otra",
            "name": "Beto",
            "email": "beto-leads@prisma.com",
            "password": "contrasena-segura",
            "accept_terms": True,
            "accept_privacy": True,
        },
    )
    assert other.status_code == 201, other.text
    second = client.post(
        "/api/clients",
        json={"name": "Dos", "industry": "", "description": "", "general_context": "", "is_active": True},
    ).json()
    assert client.get(f"/api/clients/{first['id']}/leads").status_code == 404
    assert client.get(f"/api/clients/{second['id']}/leads").json() == []
    assert client.get(f"/api/clients/{second['id']}/leads/{lead_id}").status_code == 404


def test_whatsapp_inbound_creates_lead_when_enabled(authenticated_client: TestClient, monkeypatch):
    customer, _agent, channel = _setup_channel(authenticated_client)
    customer_id = customer["id"]
    put = authenticated_client.put(
        f"/api/clients/{customer_id}/lead-capture",
        json={"enabled": True, "sources": ["whatsapp"], "auto_tags": ["wa"]},
    )
    assert put.status_code == 200, put.text

    monkeypatch.setattr(
        whatsapp_inbound_service,
        "run_completion",
        AsyncMock(return_value=ai_service.Completion(text="Hola")),
    )
    monkeypatch.setattr(webhook_router, "send_text", AsyncMock(return_value="wamid.out-1"))
    payload = _webhook_payload(
        [{"from": "5730011", "id": "wamid.in-lead-1", "type": "text", "text": {"body": "Quiero reservar"}}],
        contacts=[{"wa_id": "5730011", "profile": {"name": "Maria"}}],
    )
    response = _post_signed(authenticated_client, channel["id"], payload)
    assert response.status_code == 200, response.text

    leads = authenticated_client.get(f"/api/clients/{customer_id}/leads").json()
    assert len(leads) == 1
    assert leads[0]["contact"]["name"] == "Maria"
    assert leads[0]["contact"]["phone"] == "5730011"
    assert leads[0]["conversation_id"]
    assert leads[0]["source"] == "whatsapp"


def test_retry_after_enabling(authenticated_client: TestClient):
    client = authenticated_client.post(
        "/api/clients",
        json={"name": "Retry Co", "industry": "", "description": "", "general_context": "", "is_active": True},
    ).json()
    settings = authenticated_client.get(f"/api/clients/{client['id']}/lead-capture").json()
    token = settings["ingest_token"]
    skipped = authenticated_client.post(
        f"/api/public/lead-capture/{token}",
        json={"source": "form", "name": "Carla", "email": "carla@retry.com"},
    )
    assert skipped.status_code == 201
    assert skipped.json()["status"] == "skipped"

    authenticated_client.put(
        f"/api/clients/{client['id']}/lead-capture",
        json={"enabled": True, "sources": ["form"]},
    )
    events = authenticated_client.get(f"/api/clients/{client['id']}/lead-capture/events").json()
    assert events[0]["status"] == "skipped"
    retried = authenticated_client.post(f"/api/clients/{client['id']}/lead-capture/events/{events[0]['id']}/retry")
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "success"
    assert authenticated_client.get(f"/api/clients/{client['id']}/leads").json()[0]["contact"]["email"] == "carla@retry.com"


def test_detection_rule_without_llm():
    detector = LeadDetectionService()
    assert detector.detect(source="form", enabled_sources={"form"}).should_create_lead
    assert not detector.detect(source="whatsapp", enabled_sources={"form"}).should_create_lead


def test_open_lead_is_updated_not_duplicated(authenticated_client: TestClient):
    client = authenticated_client.post(
        "/api/clients",
        json={"name": "Dedupe Co", "industry": "", "description": "", "general_context": "", "is_active": True},
    ).json()
    settings = authenticated_client.put(
        f"/api/clients/{client['id']}/lead-capture",
        json={"enabled": True, "sources": ["form"]},
    ).json()
    first = authenticated_client.post(
        f"/api/public/lead-capture/{settings['ingest_token']}",
        json={"source": "form", "name": "Ana", "email": "ana@dedupe.com", "phone": "573001112233"},
    )
    second = authenticated_client.post(
        f"/api/public/lead-capture/{settings['ingest_token']}",
        json={"source": "form", "name": "Ana Lopez", "email": "ana@dedupe.com"},
    )
    assert first.json()["lead_id"] == second.json()["lead_id"]
    listed = authenticated_client.get(f"/api/clients/{client['id']}/leads").json()
    assert len(listed) == 1


def test_closed_lead_allows_a_new_opportunity(authenticated_client: TestClient):
    client = authenticated_client.post(
        "/api/clients",
        json={"name": "Won Co", "industry": "", "description": "", "general_context": "", "is_active": True},
    ).json()
    settings = authenticated_client.put(
        f"/api/clients/{client['id']}/lead-capture",
        json={"enabled": True, "sources": ["form"]},
    ).json()
    created = authenticated_client.post(
        f"/api/public/lead-capture/{settings['ingest_token']}",
        json={"source": "form", "name": "Beto", "email": "beto@won.com"},
    )
    lead_id = created.json()["lead_id"]
    stages = {row["slug"]: row["id"] for row in settings["pipeline"]["stages"]}
    patched = authenticated_client.patch(
        f"/api/clients/{client['id']}/leads/{lead_id}",
        json={"stage_id": stages["won"]},
    )
    assert patched.status_code == 200, patched.text
    again = authenticated_client.post(
        f"/api/public/lead-capture/{settings['ingest_token']}",
        json={"source": "form", "name": "Beto", "email": "beto@won.com"},
    )
    assert again.status_code == 201
    assert again.json()["lead_id"] != lead_id
    listed = authenticated_client.get(f"/api/clients/{client['id']}/leads").json()
    assert len(listed) == 2


def test_manual_create_and_list_filters(authenticated_client: TestClient):
    client = authenticated_client.post(
        "/api/clients",
        json={"name": "Manual Co", "industry": "", "description": "", "general_context": "", "is_active": True},
    ).json()
    created = authenticated_client.post(
        f"/api/clients/{client['id']}/leads",
        json={"name": "Carla", "email": "carla@manual.com", "company": "Acme", "notes": "Llamar mañana"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["contact"]["company"] == "Acme"
    assert created.json()["activities"]
    listed = authenticated_client.get(f"/api/clients/{client['id']}/leads?q=carla")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    stats = authenticated_client.get(f"/api/clients/{client['id']}/leads/stats")
    assert stats.status_code == 200
    assert stats.json()["new_count"] == 1
    assert stats.json()["unassigned_count"] == 1


def test_patch_isolation(authenticated_client: TestClient, client: TestClient):
    first = authenticated_client.post(
        "/api/clients",
        json={"name": "Privado", "industry": "", "description": "", "general_context": "", "is_active": True},
    ).json()
    lead = authenticated_client.post(
        f"/api/clients/{first['id']}/leads",
        json={"name": "Nico"},
    ).json()
    authenticated_client.post("/api/auth/logout")
    other = client.post(
        "/api/auth/register",
        json={
            "agency_name": "OtraPatch",
            "name": "Beto",
            "email": "beto-patch@prisma.com",
            "password": "contrasena-segura",
            "accept_terms": True,
            "accept_privacy": True,
        },
    )
    assert other.status_code == 201, other.text
    assert client.patch(f"/api/clients/{first['id']}/leads/{lead['id']}", json={"notes": "hack"}).status_code == 404
    second = client.post(
        "/api/clients",
        json={"name": "Otro", "industry": "", "description": "", "general_context": "", "is_active": True},
    ).json()
    assert client.patch(f"/api/clients/{second['id']}/leads/{lead['id']}", json={"notes": "hack"}).status_code == 404
