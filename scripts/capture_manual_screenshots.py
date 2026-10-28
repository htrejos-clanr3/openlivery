#!/usr/bin/env python3
"""Capture UI screenshots for end-user manual and run a real playground attempt."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000/api"
EMAIL = "hernan@lacasona.example.com"
PASSWORD = "R3SecurePass123"
AGENT_ID = "d453c78f-f45e-4505-8018-57d0cb95c289"
OUT = Path(__file__).resolve().parents[1] / "docs" / "manual-usuario" / "screenshots"


class ApiClient:
    def __init__(self) -> None:
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def request(self, method: str, url: str, body: dict | None = None) -> tuple[int, object]:
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=30) as resp:
                raw = resp.read()
                payload: object = None
                if raw:
                    payload = json.loads(raw.decode())
                return resp.status, payload
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                payload = json.loads(raw.decode()) if raw else None
            except json.JSONDecodeError:
                payload = raw.decode() if raw else None
            return exc.code, payload


def api_playground_probe() -> dict:
    client = ApiClient()
    _, me = client.request("POST", f"{API}/auth/login", {"email": EMAIL, "password": PASSWORD})
    assert me and isinstance(me, dict), "login failed"

    _, agents = client.request("GET", f"{API}/agents")
    agent = next((a for a in agents if a["id"] == AGENT_ID), None) if isinstance(agents, list) else None
    if not agent and isinstance(agents, list) and agents:
        agent = agents[0]

    provider_ready = False
    if agent:
        _, creds = client.request("GET", f"{API}/providers")
        if isinstance(creds, list):
            provider_ready = any(item.get("configured") for item in creds)

    conv_status, conversation = client.request("POST", f"{API}/conversations", {"agent_id": agent["id"]})
    msg_status, msg_payload = client.request(
        "POST",
        f"{API}/conversations/{conversation['id']}/messages",
        {"content": "Hola, ¿qué platos recomiendan hoy?"},
    )

    assistant_reply = None
    if msg_status == 200 and isinstance(msg_payload, dict):
        for message in msg_payload.get("messages", []):
            if message.get("role") == "assistant":
                assistant_reply = (message.get("content") or "")[:200]

    return {
        "agent_name": agent.get("name") if agent else None,
        "agent_model": agent.get("model") if agent else None,
        "provider_key_configured": provider_ready,
        "conversation_created": conv_status == 201,
        "message_status": msg_status,
        "assistant_reply_preview": assistant_reply,
        "blocked_reason": msg_payload.get("detail") if msg_status == 400 and isinstance(msg_payload, dict) else None,
    }


def capture_screenshots() -> list[str]:
    OUT.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    routes = [
        ("01-login", f"{BASE}/login"),
        ("02-dashboard", f"{BASE}/"),
        ("03-clients", f"{BASE}/clients"),
        ("04-agents", f"{BASE}/agents"),
        ("05-agent-detail", f"{BASE}/agents/{AGENT_ID}"),
        ("06-playground", f"{BASE}/playground?agent={AGENT_ID}"),
        ("07-inbox", f"{BASE}/inbox"),
        ("08-settings", f"{BASE}/settings"),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, locale="es-CO")
        page = context.new_page()

        # Login first
        page.goto(f"{BASE}/login", wait_until="networkidle")
        page.fill('input[name="email"]', EMAIL)
        page.fill('input[name="password"]', PASSWORD)
        page.click("button.button.primary.full")
        page.wait_for_url(f"{BASE}/**", timeout=15000)
        time.sleep(1)

        for slug, url in routes:
            page.goto(url, wait_until="networkidle")
            time.sleep(1.2)
            if slug == "06-playground":
                textarea = page.locator("textarea[name='message']")
                if textarea.count():
                    textarea.fill("Hola, quiero pedir una lasagna para dos personas")
                    page.click("form.composer button[type='submit'], form.composer button:not([type='button'])")
                    time.sleep(4)
            path = OUT / f"{slug}.png"
            page.screenshot(path=str(path), full_page=True)
            saved.append(str(path.relative_to(OUT.parents[1])))

        browser.close()
    return saved


def main() -> int:
    print("=== Playground probe (API) ===")
    try:
        probe = api_playground_probe()
        print(json.dumps(probe, indent=2, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        print(f"API probe failed: {exc}", file=sys.stderr)
        probe = {"error": str(exc)}

    print("\n=== UI screenshots ===")
    try:
        files = capture_screenshots()
        for f in files:
            print("saved", f)
    except Exception as exc:  # noqa: BLE001
        print(f"Screenshot capture failed: {exc}", file=sys.stderr)
        return 1

    summary = OUT.parent / "RESULTADO-CORRIDA.md"
    summary.write_text(
        "\n".join(
            [
                "# Corrida manual — playground y capturas",
                "",
                f"Fecha: {time.strftime('%Y-%m-%d %H:%M')}",
                "",
                "## Manual de usuario final",
                "",
                "No existe un manual dedicado para el operador de agencia / usuario final en el repositorio.",
                "Documentación disponible:",
                "- `docs/self-hosting.md` — instalación y operación técnica",
                "- `README.md` — visión general",
                "- Sitio externo referenciado en README: https://fast-livery.com/docs",
                "",
                "## Corrida real en playground",
                "",
                "```json",
                json.dumps(probe, indent=2, ensure_ascii=False),
                "```",
                "",
                "## Capturas generadas",
                "",
                *[f"- `{Path(f).name}`" for f in files],
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"\nWrote {summary.relative_to(OUT.parents[1])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
