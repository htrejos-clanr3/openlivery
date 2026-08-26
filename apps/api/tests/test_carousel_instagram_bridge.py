"""Bridge: approved Pomelli carousel → Instagram Content Publishing."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest

os.environ["INSTAGRAM_PUBLISHING_MOCK_MODE"] = "true"
os.environ.setdefault("INSTAGRAM_SCHEDULER_ENABLED", "false")

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()


def _png() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _approve_carousel(client, customer_id: str, portal_slug: str) -> dict:
    created = client.post(
        "/api/carousels",
        json={
            "client_id": customer_id,
            "title": "5 beneficios",
            "brief": "Automatizar procesos",
            "language": "es",
            "slide_count": 3,
            "generate": True,
            "with_images": False,
        },
    )
    assert created.status_code == 201, created.text
    carousel = created.json()

    # Attach mock images directly via DB so publish validation passes.
    from app.database import SessionLocal
    from app.models import CarouselSlide

    db = SessionLocal()
    try:
        slides = db.query(CarouselSlide).filter(CarouselSlide.carousel_id == carousel["id"]).all()
        for slide in slides:
            slide.image_data = _png()
            slide.image_mime = "image/png"
        db.commit()
    finally:
        db.close()

    for slide in carousel["slides"]:
        assert client.post(f"/api/carousels/{carousel['id']}/slides/{slide['id']}/agency-approve").status_code == 200
    assert client.post(f"/api/carousels/{carousel['id']}/submit-review").status_code == 200

    client.post(
        f"/api/clients/{customer_id}/portal-users",
        json={"name": "Dueno", "email": "owner@bridge.example.com", "password": "PortalPass123"},
    )
    client.patch(f"/api/clients/{customer_id}/portal", json={"portal_enabled": True, "portal_title": "Portal"})
    login = client.post(
        f"/api/portal/{portal_slug}/login",
        json={"email": "owner@bridge.example.com", "password": "PortalPass123"},
    )
    assert login.status_code == 200, login.text
    detail = client.get(f"/api/portal/{portal_slug}/carousels/{carousel['id']}").json()
    for slide in detail["slides"]:
        assert (
            client.post(f"/api/portal/{portal_slug}/carousels/{carousel['id']}/slides/{slide['id']}/approve").status_code
            == 200
        )
    approved = client.post(f"/api/portal/{portal_slug}/carousels/{carousel['id']}/approve-set")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    return approved.json()


def test_carousel_publish_now_via_instagram_bridge(authenticated_client):
    client = authenticated_client
    customer = client.post(
        "/api/clients",
        json={"name": "Bridge Co", "industry": "Software", "description": "Dev", "general_context": "PYME"},
    ).json()

    # Connect Instagram (mock)
    session = client.post(f"/api/instagram/channels/{customer['id']}/oauth/session")
    assert session.status_code == 200, session.text
    complete = client.post(
        f"/api/instagram/channels/{customer['id']}/oauth/complete",
        json={"state": session.json()["state"], "use_mock": True},
    )
    assert complete.status_code == 200, complete.text

    carousel = _approve_carousel(client, customer["id"], customer["portal_slug"])
    published = client.post(f"/api/carousels/{carousel['id']}/publish")
    assert published.status_code == 200, published.text
    body = published.json()
    assert body["status"] == "published"
    assert body["ig_media_id"]
    assert body["content_item_id"]
    assert body["publication_id"]
    assert body["publish_error"] is None


def test_carousel_schedule_queues_publication(authenticated_client):
    client = authenticated_client
    customer = client.post(
        "/api/clients",
        json={"name": "Schedule Co", "industry": "Software", "description": "Dev", "general_context": "PYME"},
    ).json()
    session = client.post(f"/api/instagram/channels/{customer['id']}/oauth/session")
    client.post(
        f"/api/instagram/channels/{customer['id']}/oauth/complete",
        json={"state": session.json()["state"], "use_mock": True},
    )
    carousel = _approve_carousel(client, customer["id"], customer["portal_slug"])
    when = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    scheduled = client.post(f"/api/carousels/{carousel['id']}/schedule", json={"scheduled_at": when})
    assert scheduled.status_code == 200, scheduled.text
    body = scheduled.json()
    assert body["status"] == "scheduled"
    assert body["publication_id"]
    assert body["content_item_id"]
    assert body["publish_error"] is None

    pubs = client.get(f"/api/instagram/channels/{customer['id']}/publications?status=QUEUED")
    assert pubs.status_code == 200
    assert any(p["id"] == body["publication_id"] for p in pubs.json())
