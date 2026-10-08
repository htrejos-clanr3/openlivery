#!/usr/bin/env python3
"""End-to-end system smoke against a running OpenLivery Docker stack.

Covers: health → register/legal → client/agent → LinkedIn/Instagram mock connect
→ carousel agency/portal approval → multi-network publish → logout/login → UI pages.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "http://127.0.0.1:8000"
BASE = f"{API}/api"
WEB = "http://127.0.0.1:3001"
EMAIL = f"e2e-system-{int(time.time())}@example.com"
PASSWORD = "E2ESecurePass123!"
PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


class Client:
    def __init__(self) -> None:
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def request(
        self,
        method: str,
        url: str,
        body: dict | None = None,
        expect: int | None = 200,
    ) -> tuple[int, object]:
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=90) as resp:
                raw = resp.read()
                payload: object = None
                if raw:
                    try:
                        payload = json.loads(raw.decode())
                    except json.JSONDecodeError:
                        payload = raw.decode()
                if expect is not None and resp.status != expect:
                    raise AssertionError(f"{method} {url} -> {resp.status}, expected {expect}: {payload}")
                return resp.status, payload
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                payload = json.loads(raw.decode()) if raw else None
            except json.JSONDecodeError:
                payload = raw.decode() if raw else None
            if expect is not None and exc.code != expect:
                raise AssertionError(f"{method} {url} -> {exc.code}, expected {expect}: {payload}") from exc
            return exc.code, payload


def ok(label: str) -> None:
    print(f"OK  {label}")


def attach_slide_images(carousel_id: str) -> None:
    """Inject 1x1 PNG into every slide via the API container (publish requires image bytes)."""
    hex_png = PNG_1X1.hex()
    script = f"""
from app.database import SessionLocal
from app.models import CarouselSlide
import uuid
cid = uuid.UUID({carousel_id!r})
data = bytes.fromhex({hex_png!r})
db = SessionLocal()
try:
    slides = db.query(CarouselSlide).filter(CarouselSlide.carousel_id == cid).all()
    assert slides, "no slides"
    for s in slides:
        s.image_data = data
        s.image_mime = "image/png"
    db.commit()
    print(len(slides))
finally:
    db.close()
"""
    proc = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            ".env.docker",
            "exec",
            "-T",
            "api",
            "python",
            "-c",
            script,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(f"attach images failed: {proc.stderr or proc.stdout}")
    ok(f"attached images to {proc.stdout.strip()} slides")


def consent(channel: str, client_id: str) -> dict:
    return {
        "consent": {
            "channel": channel,
            "client_id": client_id,
            "admin_confirmed": True,
            "no_password_stored": True,
            "ai_disclosure_acknowledged": channel == "instagram",
        }
    }


def main() -> int:
    client = Client()
    failures: list[str] = []
    print("=== E2E SYSTEM ===")
    print(f"API={API} WEB={WEB} email={EMAIL}")

    try:
        # Health
        _, health = client.request("GET", f"{API}/health")
        assert health == {"status": "ok"}, health
        ok("api health")

        status, _ = client.request("GET", f"{WEB}/login", expect=None)
        if status != 200:
            failures.append(f"web /login -> {status}")
        else:
            ok("web /login")

        status, _ = client.request("GET", f"{WEB}/channels", expect=None)
        if status not in {200, 307, 302, 401}:
            failures.append(f"web /channels -> {status}")
        else:
            ok(f"web /channels ({status})")

        # Legal documents public
        _, docs = client.request("GET", f"{BASE}/legal/documents")
        assert isinstance(docs, dict) and docs.get("tos_version")
        ok(f"legal documents tos={docs['tos_version']}")

        # Register without terms must fail
        status, _ = client.request(
            "POST",
            f"{BASE}/auth/register",
            {
                "agency_name": "No Terms E2E",
                "name": "No Terms",
                "email": f"noterms-{int(time.time())}@example.com",
                "password": PASSWORD,
                "accept_terms": False,
                "accept_privacy": True,
            },
            expect=400,
        )
        ok("register blocked without terms")

        # Register with legal gates
        _, user = client.request(
            "POST",
            f"{BASE}/auth/register",
            {
                "agency_name": "E2E System Agency",
                "name": "QA System",
                "email": EMAIL,
                "password": PASSWORD,
                "accept_terms": True,
                "accept_privacy": True,
            },
            expect=201,
        )
        assert isinstance(user, dict) and user["email"] == EMAIL
        ok(f"register agency={user['agency']['name']}")

        _, me = client.request("GET", f"{BASE}/auth/me")
        assert isinstance(me, dict) and me["email"] == EMAIL
        ok("auth/me")

        _, platform = client.request("GET", f"{BASE}/legal/platform/status")
        assert isinstance(platform, dict) and platform.get("platform_ready") is True
        ok("legal platform ready")

        # Client + agent
        _, restaurant = client.request(
            "POST",
            f"{BASE}/clients",
            {
                "name": "Cliente E2E System",
                "industry": "Restaurantes",
                "description": "Prueba e2e sistema",
                "general_context": "Horario 11-22. Chapinero.",
                "is_active": True,
            },
            expect=201,
        )
        assert isinstance(restaurant, dict)
        client_id = restaurant["id"]
        portal_slug = restaurant["portal_slug"]
        ok(f"client {client_id}")

        _, agent = client.request(
            "POST",
            f"{BASE}/agents",
            {
                "client_id": client_id,
                "name": "Agente E2E",
                "description": "Agente de prueba",
                "instructions": "Responde en espanol sobre el menu.",
                "personality": "Amigable",
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "widget_enabled": True,
                "widget_greeting": "Hola E2E",
                "is_active": True,
            },
            expect=201,
        )
        assert isinstance(agent, dict)
        agent_id = agent["id"]
        public_id = agent["widget_public_id"]
        ok(f"agent {agent_id}")

        client.request(
            "POST",
            f"{BASE}/agents/{agent_id}/qa",
            {"question": "Precio lasagna?", "answer": "28000 COP"},
            expect=201,
        )
        ok("agent QA")

        _, widget = client.request("GET", f"{BASE}/widget/{public_id}")
        assert isinstance(widget, dict) and widget.get("title")
        ok("widget config")

        # Conversations gated without provider key
        _, conversation = client.request("POST", f"{BASE}/conversations", {"agent_id": agent_id}, expect=201)
        assert isinstance(conversation, dict)
        status, err = client.request(
            "POST",
            f"{BASE}/conversations/{conversation['id']}/messages",
            {"content": "Hola"},
            expect=400,
        )
        ok(f"conversation gated without provider ({err})")

        # Instagram + LinkedIn mock connect with legal B
        status, _ = client.request(
            "POST",
            f"{BASE}/instagram/channels/{client_id}/oauth/session",
            {},
            expect=422,
        )
        ok("instagram oauth requires consent body")

        _, ig_session = client.request(
            "POST",
            f"{BASE}/instagram/channels/{client_id}/oauth/session",
            consent("instagram", client_id),
        )
        assert isinstance(ig_session, dict) and ig_session.get("state")
        _, ig = client.request(
            "POST",
            f"{BASE}/instagram/channels/{client_id}/oauth/complete",
            {"state": ig_session["state"], "use_mock": True},
        )
        assert isinstance(ig, dict) and ig.get("status") == "connected"
        ok("instagram mock connected")

        status, _ = client.request(
            "POST",
            f"{BASE}/linkedin/channels/{client_id}/oauth/session",
            {},
            expect=422,
        )
        ok("linkedin oauth requires consent body")

        _, li_session = client.request(
            "POST",
            f"{BASE}/linkedin/channels/{client_id}/oauth/session",
            consent("linkedin", client_id),
        )
        assert isinstance(li_session, dict) and li_session.get("state")
        _, li = client.request(
            "POST",
            f"{BASE}/linkedin/channels/{client_id}/oauth/complete",
            {"state": li_session["state"], "use_mock": True},
        )
        assert isinstance(li, dict) and li.get("status") == "connected"
        ok("linkedin mock connected")

        # WhatsApp Cloud channel read (may be disconnected)
        status, wa = client.request("GET", f"{BASE}/whatsapp-cloud/channels/{client_id}", expect=None)
        if status == 200:
            ok(f"whatsapp-cloud channel status={getattr(wa, 'get', lambda *_: None)('status') if isinstance(wa, dict) else wa}")
        else:
            ok(f"whatsapp-cloud channel endpoint reachable ({status})")

        # Carousel create → agency approve → portal approve → publish IG+LI
        _, carousel = client.request(
            "POST",
            f"{BASE}/carousels",
            {
                "client_id": client_id,
                "title": "Carrusel E2E System",
                "brief": "Beneficios de automatizar pedidos",
                "language": "es",
                "slide_count": 3,
                "generate": True,
                "with_images": False,
            },
            expect=201,
        )
        assert isinstance(carousel, dict)
        carousel_id = carousel["id"]
        assert len(carousel["slides"]) == 3
        ok(f"carousel created {carousel_id}")

        attach_slide_images(carousel_id)

        for slide in carousel["slides"]:
            client.request("POST", f"{BASE}/carousels/{carousel_id}/slides/{slide['id']}/agency-approve")
        client.request("POST", f"{BASE}/carousels/{carousel_id}/submit-review")
        ok("carousel submitted to portal review")

        client.request(
            "POST",
            f"{BASE}/clients/{client_id}/portal-users",
            {"name": "Dueno E2E", "email": "owner-e2e@example.com", "password": "PortalPass123"},
            expect=201,
        )
        client.request(
            "PATCH",
            f"{BASE}/clients/{client_id}/portal",
            {"portal_enabled": True, "portal_title": "Portal E2E"},
        )
        client.request(
            "POST",
            f"{BASE}/portal/{portal_slug}/login",
            {"email": "owner-e2e@example.com", "password": "PortalPass123"},
        )
        _, portal_detail = client.request("GET", f"{BASE}/portal/{portal_slug}/carousels/{carousel_id}")
        assert isinstance(portal_detail, dict)
        for slide in portal_detail["slides"]:
            client.request(
                "POST",
                f"{BASE}/portal/{portal_slug}/carousels/{carousel_id}/slides/{slide['id']}/approve",
            )
        _, approved = client.request("POST", f"{BASE}/portal/{portal_slug}/carousels/{carousel_id}/approve-set")
        assert isinstance(approved, dict) and approved["status"] == "approved"
        ok("carousel client-approved")

        # Publish without approval flags must stay pending / rejected
        status, denied = client.request(
            "POST",
            f"{BASE}/carousels/{carousel_id}/publish",
            {"destinations": ["instagram", "linkedin"]},
            expect=400,
        )
        ok("publish blocked without human approval")

        status, denied_empty = client.request(
            "POST",
            f"{BASE}/carousels/{carousel_id}/publish",
            {"destinations": [], "human_approved": True, "reviewed_exact_content": True},
            expect=400,
        )
        ok("publish blocked with empty destinations")

        _, published = client.request(
            "POST",
            f"{BASE}/carousels/{carousel_id}/publish",
            {
                "destinations": ["instagram", "linkedin"],
                "human_approved": True,
                "reviewed_exact_content": True,
            },
        )
        assert isinstance(published, dict)
        assert published["status"] == "published", published
        assert published["publish_results"]["instagram"]["ok"] is True
        assert published["publish_results"]["linkedin"]["ok"] is True
        assert published.get("ig_media_id")
        assert published.get("linkedin_post_id")
        ok(
            "carousel published IG+LI "
            f"ig={published['ig_media_id']} li={published['linkedin_post_id']}"
        )

        # Auth cycle
        client.request("POST", f"{BASE}/auth/logout", expect=204)
        client.request("GET", f"{BASE}/auth/me", expect=401)
        client.request("POST", f"{BASE}/auth/login", {"email": EMAIL, "password": PASSWORD})
        client.request("GET", f"{BASE}/auth/me")
        ok("logout/login")

        # UI pages smoke (authenticated cookie may not apply to Next — just HTTP reachability)
        for path in ("/login", "/clients", "/carousels", "/channels"):
            st, _ = client.request("GET", f"{WEB}{path}", expect=None)
            if st >= 500:
                failures.append(f"web {path} -> {st}")
            else:
                ok(f"web {path} ({st})")

    except Exception as exc:  # noqa: BLE001 — surface as e2e failure
        failures.append(str(exc))
        print(f"FAIL {exc}")

    print("=== SUMMARY ===")
    if failures:
        print("FAILURES:")
        for item in failures:
            print(" -", item)
        return 1
    print("ALL E2E SYSTEM CHECKS PASSED")
    print(json.dumps({"email": EMAIL, "api": API, "web": WEB}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
