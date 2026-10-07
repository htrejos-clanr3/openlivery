"""POC A: approved carousel → Instagram and/or LinkedIn MultiImage."""

from __future__ import annotations

import os

import pytest

os.environ["INSTAGRAM_PUBLISHING_MOCK_MODE"] = "true"
os.environ["LINKEDIN_MOCK_MODE"] = "true"
os.environ.setdefault("INSTAGRAM_SCHEDULER_ENABLED", "false")

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from tests.test_carousel_instagram_bridge import _approve_carousel, _consent  # noqa: E402


def _li_consent(client_id: str):
    return {
        "consent": {
            "channel": "linkedin",
            "client_id": client_id,
            "admin_confirmed": True,
            "no_password_stored": True,
            "ai_disclosure_acknowledged": False,
        }
    }


def test_carousel_publish_instagram_and_linkedin(authenticated_client):
    client = authenticated_client
    customer = client.post(
        "/api/clients",
        json={"name": "Multi Pub Co", "industry": "Software", "description": "Dev", "general_context": "PYME"},
    ).json()

    ig_session = client.post(
        f"/api/instagram/channels/{customer['id']}/oauth/session",
        json=_consent(customer["id"]),
    )
    assert ig_session.status_code == 200, ig_session.text
    assert (
        client.post(
            f"/api/instagram/channels/{customer['id']}/oauth/complete",
            json={"state": ig_session.json()["state"], "use_mock": True},
        ).status_code
        == 200
    )

    li_session = client.post(
        f"/api/linkedin/channels/{customer['id']}/oauth/session",
        json=_li_consent(customer["id"]),
    )
    assert li_session.status_code == 200, li_session.text
    assert (
        client.post(
            f"/api/linkedin/channels/{customer['id']}/oauth/complete",
            json={"state": li_session.json()["state"], "use_mock": True},
        ).status_code
        == 200
    )

    carousel = _approve_carousel(client, customer["id"], customer["portal_slug"])
    published = client.post(
        f"/api/carousels/{carousel['id']}/publish",
        json={
            "destinations": ["instagram", "linkedin"],
            "human_approved": True,
            "reviewed_exact_content": True,
        },
    )
    assert published.status_code == 200, published.text
    body = published.json()
    assert body["status"] == "published"
    assert body["ig_media_id"]
    assert body["linkedin_post_id"]
    assert body["publish_results"]["instagram"]["ok"] is True
    assert body["publish_results"]["linkedin"]["ok"] is True
    assert body["publish_error"] is None


def test_carousel_publish_linkedin_only(authenticated_client):
    client = authenticated_client
    customer = client.post(
        "/api/clients",
        json={"name": "LI Only Co", "industry": "Software", "description": "Dev", "general_context": "PYME"},
    ).json()
    li_session = client.post(
        f"/api/linkedin/channels/{customer['id']}/oauth/session",
        json=_li_consent(customer["id"]),
    )
    client.post(
        f"/api/linkedin/channels/{customer['id']}/oauth/complete",
        json={"state": li_session.json()["state"], "use_mock": True},
    )
    carousel = _approve_carousel(client, customer["id"], customer["portal_slug"])
    published = client.post(
        f"/api/carousels/{carousel['id']}/publish",
        json={"destinations": ["linkedin"], "human_approved": True, "reviewed_exact_content": True},
    )
    assert published.status_code == 200, published.text
    body = published.json()
    assert body["status"] == "published"
    assert body["linkedin_post_id"]
    assert body["publish_results"]["linkedin"]["ok"] is True


def test_carousel_publish_requires_approval_flags(authenticated_client):
    client = authenticated_client
    customer = client.post(
        "/api/clients",
        json={"name": "Flags Co", "industry": "Software", "description": "Dev", "general_context": "PYME"},
    ).json()
    carousel = _approve_carousel(client, customer["id"], customer["portal_slug"])
    denied = client.post(
        f"/api/carousels/{carousel['id']}/publish",
        json={"destinations": ["instagram"], "human_approved": False, "reviewed_exact_content": True},
    )
    assert denied.status_code == 400
