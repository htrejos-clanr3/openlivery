import os

from fastapi.testclient import TestClient

os.environ["LINKEDIN_MOCK_MODE"] = "true"

from app.config import get_settings
from app.services.linkedin.generate import clean_text, load_hooks, score_profile_heuristic

get_settings.cache_clear()


def test_hooks_catalog_has_twenty_one():
    pack = load_hooks()
    assert len(pack["hooks"]) == 21
    assert pack["hooks"][0]["id"] == 1


def test_humanize_strips_em_dash_and_slop():
    cleaned, report, panel = clean_text("Let’s leverage this — it’s crucial in today’s fast-paced world.")
    assert "—" not in cleaned
    assert "leverage" not in cleaned.lower()
    assert panel["human_score"] >= 0
    assert report["typographic"] or report["lexical"]


def test_linkedin_desk_generate_and_profile(authenticated_client: TestClient):
    client = authenticated_client
    customer = client.post(
        "/api/clients",
        json={"name": "La Casona LinkedIn", "industry": "restaurants", "description": "", "general_context": "", "is_active": True},
    ).json()
    cid = customer["id"]

    channel = client.get(f"/api/linkedin/channels/{cid}")
    assert channel.status_code == 200
    assert channel.json()["publishes"] is False
    assert channel.json()["connection_mode"] == "copy_paste"

    saved = client.patch(
        f"/api/linkedin/channels/{cid}",
        json={"profile_url": "https://www.linkedin.com/in/demo", "voice_notes": "Ayudo a restaurantes. Nunca digo leverage."},
    )
    assert saved.status_code == 200
    assert saved.json()["profile_url"].endswith("/demo")

    options = client.get("/api/linkedin/oauth/options")
    assert options.status_code == 200
    assert options.json()["oauth_available"] is True
    assert "w_member_social" in options.json()["scopes"]

    session = client.post(f"/api/linkedin/channels/{cid}/oauth/session")
    assert session.status_code == 200, session.text
    connected = client.post(
        f"/api/linkedin/channels/{cid}/oauth/complete",
        json={"state": session.json()["state"], "use_mock": True},
    )
    assert connected.status_code == 200, connected.text
    assert connected.json()["status"] == "connected"
    assert connected.json()["publishes"] is True
    assert connected.json()["access_token_configured"] is True
    assert "access_token" not in connected.json()

    hooks = client.get("/api/linkedin/hooks")
    assert hooks.status_code == 200
    assert len(hooks.json()["hooks"]) == 21

    post = client.post(
        f"/api/linkedin/channels/{cid}/posts",
        json={"idea": "Bajamos el tiempo de propuesta de 5 horas a 20 minutos con una plantilla."},
    )
    assert post.status_code == 200, post.text
    body = post.json()
    assert body["copy_ready"]
    assert "api oficial" in body["post_at_hint"].lower() or "official api" in body["post_at_hint"].lower()
    assert len(body["hooks"]) == 3

    published = client.post(
        f"/api/linkedin/channels/{cid}/drafts/{body['draft_id']}/publish",
        json={"approved": True, "text": body["copy_ready"] + "\n\nEditado por humano."},
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    assert published.json()["provider_post_id"].startswith("urn:li:share:mock-")

    repeated = client.post(
        f"/api/linkedin/channels/{cid}/drafts/{body['draft_id']}/publish",
        json={"approved": True},
    )
    assert repeated.status_code == 200
    assert repeated.json()["provider_post_id"] == published.json()["provider_post_id"]

    profile = client.post(
        f"/api/linkedin/channels/{cid}/profile",
        json={"pasted": "Passionate about restaurants. I am a consultant. Contact me."},
    )
    assert profile.status_code == 200, profile.text
    assert profile.json()["headline"]
    assert profile.json()["about"]
    assert profile.json()["audit"]["max"] == 100

    drafts = client.get(f"/api/linkedin/channels/{cid}/drafts")
    assert drafts.status_code == 200
    assert len(drafts.json()) >= 2
    assert any(item["status"] == "published" for item in drafts.json())

    cleaned = client.post(
        f"/api/linkedin/channels/{cid}/humanize",
        json={"text": "Let’s leverage this — it’s crucial."},
    )
    assert cleaned.status_code == 200
    assert "—" not in cleaned.json()["text"]
    assert "leverage" not in cleaned.json()["text"].lower()

    disconnected = client.post(f"/api/linkedin/channels/{cid}/disconnect")
    assert disconnected.status_code == 200
    assert disconnected.json()["status"] == "disconnected"
    assert disconnected.json()["access_token_configured"] is False


def test_profile_heuristic_penalizes_passionate():
    audit = score_profile_heuristic("Passionate about sales. I am a consultant.")
    about_open = next(item for item in audit["items"] if item["id"] == "about_open")
    assert about_open["score"] < about_open["points"]


def test_publish_requires_connection_and_approval(authenticated_client: TestClient):
    client = authenticated_client
    customer = client.post(
        "/api/clients",
        json={"name": "Sin conexión", "industry": "", "description": "", "general_context": ""},
    ).json()
    generated = client.post(
        f"/api/linkedin/channels/{customer['id']}/posts",
        json={"idea": "Probamos una plantilla durante cinco días y documentamos el resultado."},
    ).json()
    denied = client.post(
        f"/api/linkedin/channels/{customer['id']}/drafts/{generated['draft_id']}/publish",
        json={"approved": False},
    )
    assert denied.status_code == 400
    not_connected = client.post(
        f"/api/linkedin/channels/{customer['id']}/drafts/{generated['draft_id']}/publish",
        json={"approved": True},
    )
    assert not_connected.status_code == 400
