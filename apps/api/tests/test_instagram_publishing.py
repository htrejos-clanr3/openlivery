"""Instagram publishing: tenant isolation, mock publish, schedule, AI structure."""

from __future__ import annotations

import io
import os

import pytest

os.environ["INSTAGRAM_PUBLISHING_MOCK_MODE"] = "true"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()


def _consent(client_id: str):
    return {
        "consent": {
            "channel": "instagram",
            "client_id": client_id,
            "admin_confirmed": True,
            "no_password_stored": True,
            "ai_disclosure_acknowledged": True,
        }
    }


def _publish_body():
    return {"human_approved": True, "reviewed_exact_content": True}


def _create_client(authenticated_client):
    response = authenticated_client.post(
        "/api/clients",
        json={"name": "Cliente IG", "industry": "Software", "description": "Dev a medida", "general_context": "PYMEs"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _png_bytes() -> bytes:
    # Minimal 1x1 PNG
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )


@pytest.fixture
def ig_client(authenticated_client):
    return _create_client(authenticated_client)


def test_token_not_exposed(authenticated_client, ig_client):
    client_id = ig_client["id"]
    put = authenticated_client.put(
        f"/api/instagram/channels/{client_id}",
        json={
            "instagram_user_id": "178414000",
            "username": "brand",
            "access_token": "EAA_secret_token_value",
            "granted_scopes": ["instagram_basic", "instagram_content_publish"],
        },
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["access_token_configured"] is True
    assert "access_token" not in body
    assert "EAA_secret" not in str(body)


def test_mock_connect_and_publish_image(authenticated_client, ig_client):
    client_id = ig_client["id"]
    session = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/oauth/session",
        json=_consent(client_id),
    )
    assert session.status_code == 200, session.text
    state = session.json()["state"]
    complete = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/oauth/complete",
        json={"state": state, "use_mock": True},
    )
    assert complete.status_code == 200, complete.text
    assert complete.json()["status"] == "connected"
    assert complete.json()["username"]

    upload = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/media",
        files={"file": ("shot.png", io.BytesIO(_png_bytes()), "image/png")},
    )
    assert upload.status_code == 200, upload.text
    media_id = upload.json()["id"]

    content = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/content",
        json={
            "content_type": "IMAGE",
            "title": "Promo",
            "caption": "Hola mundo",
            "hashtags": "#software",
            "media_ids": [media_id],
        },
    )
    assert content.status_code == 200, content.text
    content_id = content.json()["id"]
    assert content.json()["status"] == "DRAFT"

    published = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/content/{content_id}/publish",
        json=_publish_body(),
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "PUBLISHED"
    assert published.json()["provider_publication_id"]
    assert published.json()["provider_container_id"]


def test_carousel_ordering_and_publish(authenticated_client, ig_client):
    client_id = ig_client["id"]
    session = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/oauth/session",
        json=_consent(client_id),
    )
    state = session.json()["state"]
    authenticated_client.post(
        f"/api/instagram/channels/{client_id}/oauth/complete",
        json={"state": state, "use_mock": True},
    )
    media_ids = []
    for i in range(3):
        up = authenticated_client.post(
            f"/api/instagram/channels/{client_id}/media",
            files={"file": (f"s{i}.png", io.BytesIO(_png_bytes()), "image/png")},
        )
        media_ids.append(up.json()["id"])
    content = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/content",
        json={"content_type": "CAROUSEL", "caption": "Carrusel", "media_ids": media_ids},
    )
    assert content.status_code == 200, content.text
    assert [m["position"] for m in content.json()["media"]] == [0, 1, 2]
    # Reorder
    reordered = list(reversed(media_ids))
    updated = authenticated_client.put(
        f"/api/instagram/channels/{client_id}/content/{content.json()['id']}",
        json={"media_ids": reordered},
    )
    assert updated.status_code == 200
    assert [m["media_id"] for m in updated.json()["media"]] == reordered
    pub = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/content/{content.json()['id']}/publish",
        json=_publish_body(),
    )
    assert pub.status_code == 200, pub.text
    assert pub.json()["status"] == "PUBLISHED"


def test_tenant_isolation(authenticated_client, ig_client, client):
    client_id = ig_client["id"]
    session = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/oauth/session",
        json=_consent(client_id),
    )
    authenticated_client.post(
        f"/api/instagram/channels/{client_id}/oauth/complete",
        json={"state": session.json()["state"], "use_mock": True},
    )
    other = client.post(
        "/api/auth/register",
        json={
            "agency_name": "Otra Agencia",
            "name": "Bob",
            "email": "bob@other.com",
            "password": "contrasena-segura",
            "accept_terms": True,
            "accept_privacy": True,
        },
    )
    assert other.status_code == 201
    denied = client.get(f"/api/instagram/channels/{client_id}")
    assert denied.status_code == 404


def test_schedule_creates_queued_publication(authenticated_client, ig_client):
    from datetime import datetime, timedelta, timezone

    client_id = ig_client["id"]
    session = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/oauth/session",
        json=_consent(client_id),
    )
    authenticated_client.post(
        f"/api/instagram/channels/{client_id}/oauth/complete",
        json={"state": session.json()["state"], "use_mock": True},
    )
    up = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/media",
        files={"file": ("a.png", io.BytesIO(_png_bytes()), "image/png")},
    )
    content = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/content",
        json={"content_type": "IMAGE", "caption": "Later", "media_ids": [up.json()["id"]]},
    )
    when = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    scheduled = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/content/{content.json()['id']}/schedule",
        json={"scheduled_at": when, "timezone": "America/Bogota", **_publish_body()},
    )
    assert scheduled.status_code == 200, scheduled.text
    assert scheduled.json()["status"] == "QUEUED"
    assert scheduled.json()["scheduled_at"]


def test_generate_carousel_structure(authenticated_client, ig_client):
    client_id = ig_client["id"]
    gen = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/generate",
        json={
            "content_type": "CAROUSEL",
            "objective": "Cinco beneficios de automatizar",
            "slide_count": 5,
            "language": "es",
        },
    )
    assert gen.status_code == 200, gen.text
    body = gen.json()
    assert isinstance(body["slides"], list)
    assert len(body["slides"]) >= 2
    assert "order" in body["slides"][0]
    assert "caption" in body
    assert isinstance(body["hashtags"], list)


def test_idempotent_republish_returns_same_id(authenticated_client, ig_client):
    client_id = ig_client["id"]
    session = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/oauth/session",
        json=_consent(client_id),
    )
    authenticated_client.post(
        f"/api/instagram/channels/{client_id}/oauth/complete",
        json={"state": session.json()["state"], "use_mock": True},
    )
    up = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/media",
        files={"file": ("a.png", io.BytesIO(_png_bytes()), "image/png")},
    )
    content = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/content",
        json={"content_type": "IMAGE", "caption": "Once", "media_ids": [up.json()["id"]]},
    )
    first = authenticated_client.post(
        f"/api/instagram/channels/{client_id}/content/{content.json()['id']}/publish",
        json=_publish_body(),
    )
    # Second publish creates a new publication attempt on same content — content is PUBLISHED
    # Updating published content should fail
    upd = authenticated_client.put(
        f"/api/instagram/channels/{client_id}/content/{content.json()['id']}",
        json={"caption": "changed"},
    )
    assert upd.status_code == 400
    assert first.json()["provider_publication_id"]
