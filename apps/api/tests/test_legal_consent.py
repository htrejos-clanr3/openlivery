"""Legal gates: register, channel connect, publish approval."""

from __future__ import annotations

import os

import pytest

os.environ["INSTAGRAM_PUBLISHING_MOCK_MODE"] = "true"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()


def _register(client, email="legal@test.com"):
    return client.post(
        "/api/auth/register",
        json={
            "agency_name": "Legal Co",
            "name": "Owner",
            "email": email,
            "password": "contrasena-segura",
            "accept_terms": True,
            "accept_privacy": True,
        },
    )


def _client(client):
    created = client.post(
        "/api/clients",
        json={"name": "Cliente Legal", "industry": "Tech", "description": "x", "general_context": "y"},
    )
    assert created.status_code == 201
    return created.json()


def _consent(client_id: str, channel: str = "instagram"):
    return {
        "consent": {
            "channel": channel,
            "client_id": client_id,
            "admin_confirmed": True,
            "no_password_stored": True,
            "ai_disclosure_acknowledged": channel == "instagram",
        }
    }


def _png_bytes() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_register_requires_terms(client):
    denied = client.post(
        "/api/auth/register",
        json={
            "agency_name": "No Terms Co",
            "name": "No Terms",
            "email": "no-terms@test.com",
            "password": "contrasena-segura",
            "accept_terms": False,
            "accept_privacy": True,
        },
    )
    assert denied.status_code == 400


def test_oauth_session_requires_consent(authenticated_client):
    ig = _client(authenticated_client)
    denied = authenticated_client.post(f"/api/instagram/channels/{ig['id']}/oauth/session", json={})
    assert denied.status_code == 422


def test_linkedin_oauth_session_requires_consent(authenticated_client):
    os.environ["LINKEDIN_MOCK_MODE"] = "true"
    get_settings.cache_clear()
    li = _client(authenticated_client)
    denied = authenticated_client.post(f"/api/linkedin/channels/{li['id']}/oauth/session", json={})
    assert denied.status_code == 422
    ok = authenticated_client.post(
        f"/api/linkedin/channels/{li['id']}/oauth/session",
        json=_consent(li["id"], channel="linkedin"),
    )
    assert ok.status_code == 200, ok.text


def test_publish_requires_human_approval(authenticated_client):
    ig = _client(authenticated_client)
    session = authenticated_client.post(
        f"/api/instagram/channels/{ig['id']}/oauth/session",
        json=_consent(ig["id"]),
    )
    assert session.status_code == 200
    authenticated_client.post(
        f"/api/instagram/channels/{ig['id']}/oauth/complete",
        json={"state": session.json()["state"], "use_mock": True},
    )
    up = authenticated_client.post(
        f"/api/instagram/channels/{ig['id']}/media",
        files={"file": ("a.png", _png_bytes(), "image/png")},
    )
    content = authenticated_client.post(
        f"/api/instagram/channels/{ig['id']}/content",
        json={"content_type": "IMAGE", "caption": "Hola", "media_ids": [up.json()["id"]]},
    )
    denied = authenticated_client.post(
        f"/api/instagram/channels/{ig['id']}/content/{content.json()['id']}/publish",
        json={"human_approved": False, "reviewed_exact_content": False},
    )
    assert denied.status_code == 400
