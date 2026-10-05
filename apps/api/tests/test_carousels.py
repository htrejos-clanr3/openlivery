"""Carousel approval flow (agency → portal) without provider images."""

from datetime import datetime, timedelta, timezone


def test_carousel_agency_to_portal_approval(authenticated_client):
    client = authenticated_client
    customer = client.post(
        "/api/clients",
        json={"name": "La Casona", "industry": "Restaurantes", "description": "Comida", "general_context": "Menú italiano"},
    ).json()
    portal_user = client.post(
        f"/api/clients/{customer['id']}/portal-users",
        json={"name": "Dueno", "email": "dueno@lacasona.example.com", "password": "PortalPass123"},
    )
    assert portal_user.status_code == 201, portal_user.text

    client.patch(
        f"/api/clients/{customer['id']}/portal",
        json={"portal_enabled": True, "portal_title": "Portal Casona"},
    )

    created = client.post(
        "/api/carousels",
        json={
            "client_id": customer["id"],
            "title": "Menú de la semana",
            "brief": "Promociona lasagna y postres",
            "language": "es",
            "slide_count": 4,
            "generate": True,
            "with_images": False,
        },
    )
    assert created.status_code == 201, created.text
    carousel = created.json()
    assert carousel["status"] == "draft"
    assert len(carousel["slides"]) == 4

    for slide in carousel["slides"]:
        ok = client.post(f"/api/carousels/{carousel['id']}/slides/{slide['id']}/agency-approve")
        assert ok.status_code == 200
        assert ok.json()["agency_status"] == "agency_ok"

    submitted = client.post(f"/api/carousels/{carousel['id']}/submit-review")
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "in_review"

    slug = customer["portal_slug"]
    login = client.post(f"/api/portal/{slug}/login", json={"email": "dueno@lacasona.example.com", "password": "PortalPass123"})
    assert login.status_code == 200
    assert login.json()["portal_user_id"]

    listed = client.get(f"/api/portal/{slug}/carousels")
    assert listed.status_code == 200
    assert any(item["id"] == carousel["id"] for item in listed.json())

    detail = client.get(f"/api/portal/{slug}/carousels/{carousel['id']}").json()
    for slide in detail["slides"]:
        approved = client.post(f"/api/portal/{slug}/carousels/{carousel['id']}/slides/{slide['id']}/approve")
        assert approved.status_code == 200
        assert approved.json()["client_status"] == "client_ok"

    set_ok = client.post(f"/api/portal/{slug}/carousels/{carousel['id']}/approve-set")
    assert set_ok.status_code == 200
    assert set_ok.json()["status"] == "approved"

    when = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    scheduled = client.post(f"/api/carousels/{carousel['id']}/schedule", json={"scheduled_at": when})
    # Bridge requires Instagram connected + slide images.
    assert scheduled.status_code == 400, scheduled.text
    assert "Instagram" in scheduled.json()["detail"] or "image" in scheduled.json()["detail"].lower()


def test_agency_approve_set_marks_all_slides(authenticated_client):
    client = authenticated_client
    customer = client.post(
        "/api/clients",
        json={"name": "La Casona", "industry": "Restaurantes", "description": "Comida", "general_context": "Menú"},
    ).json()
    created = client.post(
        "/api/carousels",
        json={
            "client_id": customer["id"],
            "title": "Set approval",
            "brief": "Promo",
            "language": "es",
            "slide_count": 4,
            "generate": True,
            "with_images": False,
        },
    )
    assert created.status_code == 201, created.text
    carousel = created.json()
    rejected = client.post(f"/api/carousels/{carousel['id']}/slides/{carousel['slides'][0]['id']}/agency-reject")
    assert rejected.status_code == 200
    approved = client.post(f"/api/carousels/{carousel['id']}/agency-approve-set")
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["status"] == "draft"
    assert all(slide["agency_status"] == "agency_ok" for slide in body["slides"])
    submitted = client.post(f"/api/carousels/{carousel['id']}/submit-review")
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "in_review"


def test_regenerate_keeps_approved_slides(authenticated_client):
    client = authenticated_client
    customer = client.post(
        "/api/clients",
        json={"name": "La Casona", "industry": "Restaurantes", "description": "Comida", "general_context": "Menú"},
    ).json()
    created = client.post(
        "/api/carousels",
        json={
            "client_id": customer["id"],
            "title": "Keep approved",
            "brief": "Promo",
            "language": "es",
            "slide_count": 4,
            "generate": True,
            "with_images": False,
        },
    )
    assert created.status_code == 201, created.text
    carousel = created.json()
    first = carousel["slides"][0]
    ok = client.post(f"/api/carousels/{carousel['id']}/slides/{first['id']}/agency-approve")
    assert ok.status_code == 200
    regen = client.post(
        f"/api/carousels/{carousel['id']}/generate",
        json={"with_images": False, "include_approved": False},
    )
    assert regen.status_code == 200, regen.text
    slides = regen.json()["slides"]
    kept = next(slide for slide in slides if slide["id"] == first["id"])
    assert kept["agency_status"] == "agency_ok"
    assert kept["headline"] == first["headline"]
    others = [slide for slide in slides if slide["id"] != first["id"]]
    assert others
    assert all(slide["agency_status"] == "pending" for slide in others)


def test_regenerate_include_approved_replaces_all(authenticated_client):
    client = authenticated_client
    customer = client.post(
        "/api/clients",
        json={"name": "La Casona", "industry": "Restaurantes", "description": "Comida", "general_context": "Menú"},
    ).json()
    created = client.post(
        "/api/carousels",
        json={
            "client_id": customer["id"],
            "title": "Replace approved",
            "brief": "Promo",
            "language": "es",
            "slide_count": 4,
            "generate": True,
            "with_images": False,
        },
    )
    assert created.status_code == 201, created.text
    carousel = created.json()
    first_id = carousel["slides"][0]["id"]
    assert client.post(f"/api/carousels/{carousel['id']}/slides/{first_id}/agency-approve").status_code == 200
    regen = client.post(
        f"/api/carousels/{carousel['id']}/generate",
        json={"with_images": False, "include_approved": True},
    )
    assert regen.status_code == 200, regen.text
    slides = regen.json()["slides"]
    assert first_id not in {slide["id"] for slide in slides}
    assert all(slide["agency_status"] == "pending" for slide in slides)


def test_carousel_playbook_keeps_single_cta(authenticated_client):
    client = authenticated_client
    customer = client.post(
        "/api/clients",
        json={"name": "La Casona", "industry": "Restaurantes", "description": "Comida", "general_context": "Menú"},
    ).json()
    created = client.post(
        "/api/carousels",
        json={
            "client_id": customer["id"],
            "title": "Promo menú",
            "brief": "Invita a pedir el menú del día",
            "language": "es",
            "slide_count": 5,
            "generate": True,
            "with_images": False,
            "content_goal": "convert",
            "cta_instruction": "Comenta MENU",
            "hook_structure": True,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["content_goal"] == "convert"
    assert body["cta_instruction"] == "Comenta MENU"
    assert body["hook_structure"] is True
    slides = body["slides"]
    assert len(slides) == 5
    assert all(slide["cta"] == "" for slide in slides[:-1])
    assert slides[-1]["cta"] == "Comenta MENU"


def test_forgot_password_google_only_path(authenticated_client, monkeypatch):
    from app.config import get_settings
    from app.models import OAuthAccount, User
    from app.database import SessionLocal

    settings = get_settings()
    monkeypatch.setenv("AUTH_EXPOSE_RESET_TOKEN", "true")
    get_settings.cache_clear()

    me = authenticated_client.get("/api/auth/me").json()
    db = SessionLocal()
    try:
        user = db.get(User, me["id"])
        user.password_hash = None
        db.add(OAuthAccount(provider="google", subject="google-sub-1", email=user.email, user_id=user.id))
        db.commit()
        email = user.email
    finally:
        db.close()

    # Re-enable expose flag via settings object used by app
    monkeypatch.setattr("app.routers.auth.get_settings", lambda: settings.model_copy(update={"auth_expose_reset_token": True}))

    res = authenticated_client.post("/api/auth/forgot-password", json={"email": email, "audience": "agency"})
    assert res.status_code == 200
    body = res.json()
    assert body["account_kind"] == "google_only"
    assert body.get("reset_token")

    set_pw = authenticated_client.post(
        "/api/auth/set-password",
        json={"token": body["reset_token"], "password": "NewSecurePass123"},
    )
    assert set_pw.status_code == 200
    assert set_pw.json()["password_configured"] is True
