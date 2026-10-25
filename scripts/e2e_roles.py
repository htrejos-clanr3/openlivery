#!/usr/bin/env python3
"""E2E by persona: every screen must load without errors for each role.

Personas covered today: anonymous visitor (must be pushed to /login) and agency
admin (owns every screen). Portal user and widget visitor are checked through
the public endpoints only, because the product has no per-role screen yet.
"""

import json
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:3001"
OUT = Path("docs/design/e2e")
OUT.mkdir(parents=True, exist_ok=True)

ADMIN_SCREENS = [
    ("/", "inicio"), ("/clients", "clientes"), ("/clients/new", "cliente-nuevo"),
    ("/agents", "agentes"), ("/agents/new", "agente-nuevo"), ("/settings", "configuracion"),
    ("/settings/meta", "meta"), ("/playground", "playground"), ("/inbox", "inbox"),
    ("/carousels", "carruseles"), ("/automations", "automatizaciones"),
    ("/channels", "canales"), ("/manual", "manual"),
]
PUBLIC_PATHS = ["/", "/clients", "/inbox", "/manual", "/settings"]


def main() -> int:
    report = {"personas": {}, "issues": []}
    stamp = uuid.uuid4().hex[:8]
    email = f"e2e-{stamp}@example.com"

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # --- anonymous: protected screens must send the visitor to /login
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        anon = {}
        for path in PUBLIC_PATHS:
            page.goto(f"{BASE}{path}", wait_until="load")
            page.wait_for_timeout(1200)
            anon[path] = {"url": page.url.replace(BASE, ""), "login": page.url.endswith("/login")}
            if not page.url.endswith("/login"):
                report["issues"].append(f"anonymous could open {path}")
        report["personas"]["anonymous"] = anon
        ctx.close()

        # --- admin: register, seed one client and one agent, walk every screen
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)[:200]))
        page.on("response", lambda r: errors.append(f"{r.status} {r.url[:110]}") if r.status >= 500 else None)

        status = ctx.request.post(
            f"{BASE}/api/auth/register",
            data=json.dumps({
                "agency_name": "Agencia E2E", "name": "Operadora",
                "email": email, "password": "R3SecurePass123",
                "accept_terms": True, "accept_privacy": True,
            }),
            headers={"Content-Type": "application/json"},
        ).status
        admin: dict = {"register": status, "screens": {}}
        if status != 201:
            report["issues"].append(f"admin register failed: {status}")

        client = ctx.request.post(
            f"{BASE}/api/clients",
            data=json.dumps({"name": "Cliente E2E", "industry": "", "description": "", "general_context": "", "is_active": True}),
            headers={"Content-Type": "application/json"},
        ).json()
        ctx.request.post(
            f"{BASE}/api/agents",
            data=json.dumps({"client_id": client["id"], "name": "Agente E2E", "description": "", "instructions": ""}),
            headers={"Content-Type": "application/json"},
        )
        admin["screens"][f"/clients/{client['id']}"] = None
        screens = ADMIN_SCREENS + [(f"/clients/{client['id']}", "cliente-detalle")]
        for path, name in screens:
            errors.clear()
            try:
                page.goto(f"{BASE}{path}", wait_until="load", timeout=30000)
                page.wait_for_timeout(900)
                page.screenshot(path=str(OUT / f"admin-{name}.png"))
                ok = not errors and not page.url.endswith("/login")
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc)[:200])
                ok = False
            admin["screens"][path] = {"ok": ok, "errors": list(errors)}
            if not ok:
                report["issues"].append(f"admin {path}: {errors}")
        report["personas"]["admin"] = admin

        # --- public endpoints a portal user or widget visitor depends on
        public = {
            "widget_config_404": ctx.request.get(f"{BASE}/api/widget/inexistente").status,
            "portal_domain_404": ctx.request.get(f"{BASE}/api/public/portal-domain?host=noexiste.test").status,
        }
        report["personas"]["public_endpoints"] = public
        browser.close()

    Path("docs/design/e2e/report.json").write_text(json.dumps(report, indent=2))
    total = sum(len(v["screens"]) for k, v in report["personas"].items() if isinstance(v, dict) and "screens" in v)
    print("pantallas comprobadas:", total)
    print("problemas:", len(report["issues"]))
    for issue in report["issues"][:10]:
        print(" -", issue)
    return 0 if not report["issues"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
