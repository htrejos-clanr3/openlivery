"""Meta Developer Tools MCP diagnostics — mock, fallback, webhook diff/repair."""

from __future__ import annotations

import asyncio
import os

import pytest

os.environ["META_DEVTOOLS_MCP_ENABLED"] = "true"
os.environ["META_DEVTOOLS_MCP_MOCK_MODE"] = "true"
os.environ["META_DEVTOOLS_MCP_MANAGE_ENABLED"] = "true"
os.environ.setdefault("INSTAGRAM_SCHEDULER_ENABLED", "false")

from app.config import get_settings  # noqa: E402
from app.services.meta_devtools_mcp import MetaDeveloperToolsProvider, MetaMcpError  # noqa: E402
from app.services.meta_platform_health import (  # noqa: E402
    MetaPlatformHealthService,
    clear_meta_cache,
    normalize_status,
)

get_settings.cache_clear()
clear_meta_cache()


def test_normalize_status_thresholds():
    assert normalize_status(None, percentage=38) == "HEALTHY"
    assert normalize_status(None, percentage=75) == "WARNING"
    assert normalize_status(None, percentage=95) == "CRITICAL"
    assert normalize_status("throttled") == "THROTTLED"


def test_mock_health_and_api_usage_label():
    clear_meta_cache()
    svc = MetaPlatformHealthService(MetaDeveloperToolsProvider(scenario="healthy"))
    health = asyncio.run(svc.get_health(force=True))
    assert health["overall_status"] in {"HEALTHY", "WARNING"}
    assert health["api_usage"]["percentage"] == 38
    label = (health["api_usage"].get("label") or "").lower()
    assert "api" in label
    assert "access_token" not in str(health).lower()


def test_webhook_missing_diff():
    clear_meta_cache()
    svc = MetaPlatformHealthService(MetaDeveloperToolsProvider(scenario="webhook_missing"))
    inspected = asyncio.run(svc.inspect_webhooks(force=True))
    assert "message_statuses" in inspected["missing"]
    assert "messages" in inspected["present"]


def test_repair_requires_confirm():
    svc = MetaPlatformHealthService(MetaDeveloperToolsProvider(scenario="webhook_missing"))

    class _U:
        id = None
        agency_id = None

    with pytest.raises(MetaMcpError) as exc:
        asyncio.run(svc.apply_webhook_repair(confirm=False, db=None, user=_U()))  # type: ignore[arg-type]
    assert "confirm" in str(exc.value).lower()


def test_meta_endpoints_with_authenticated_client(authenticated_client):
    clear_meta_cache()
    get_settings.cache_clear()
    status = authenticated_client.get("/api/meta/status")
    assert status.status_code == 200
    assert status.json()["enabled"] is True
    assert status.json()["mock_mode"] is True
    assert "access_token" not in status.json()

    health = authenticated_client.get("/api/meta/health?force=true")
    assert health.status_code == 200
    body = health.json()
    assert body["api_usage"]["percentage"] is not None

    diag = authenticated_client.post("/api/meta/diagnostics")
    assert diag.status_code == 200
    assert diag.json()["summary"]["total"] >= 5

    hooks = authenticated_client.get("/api/meta/webhooks?force=true")
    assert hooks.status_code == 200

    test = authenticated_client.post("/api/meta/webhooks/test", json={"field": "messages"})
    assert test.status_code == 200
    assert test.json()["test_id"]
    assert test.json()["steps"]["meta_received_request"] is True

    preview = authenticated_client.get("/api/meta/webhooks/repair/preview")
    assert preview.status_code == 200

    blob = str(status.json()) + str(health.json()) + str(diag.json())
    assert "Bearer" not in blob
    assert "META_DEVTOOLS_MCP_ACCESS_TOKEN" not in blob


def test_meta_disabled_fallback(authenticated_client, monkeypatch):
    monkeypatch.setenv("META_DEVTOOLS_MCP_ENABLED", "false")
    monkeypatch.setenv("META_DEVTOOLS_MCP_MOCK_MODE", "false")
    get_settings.cache_clear()
    clear_meta_cache()
    status = authenticated_client.get("/api/meta/status")
    assert status.status_code == 200
    assert status.json()["enabled"] is False
    health = authenticated_client.get("/api/meta/health")
    assert health.status_code == 200
    assert health.json()["overall_status"] == "UNAVAILABLE"
    monkeypatch.setenv("META_DEVTOOLS_MCP_ENABLED", "true")
    monkeypatch.setenv("META_DEVTOOLS_MCP_MOCK_MODE", "true")
    get_settings.cache_clear()
