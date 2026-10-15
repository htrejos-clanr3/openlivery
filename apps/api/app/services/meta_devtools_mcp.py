"""Meta Developer Tools / Social Technologies MCP adapter.

Diagnostics only — never used for WhatsApp/Instagram message I/O.
Official endpoint: https://mcp.facebook.com/devtools (Streamable HTTP).
Tool names from Meta DevTools inventory (beta; may change).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from ..config import get_settings
from .tools.mcp_client import open_mcp_session

logger = logging.getLogger("openlivery.meta_devtools_mcp")

# Official tool names (Read / Manage). Keep as constants for one place to update.
TOOL_APP_LIST = "devtools_app_list"
TOOL_APP = "devtools_app"
TOOL_APP_REVIEW = "devtools_app_review"
TOOL_COMPLIANCE = "devtools_compliance"
TOOL_API_USAGE = "devtools_api_usage"
TOOL_WEBHOOK_LIST = "devtools_webhook_list"
TOOL_WEBHOOK_MANAGE = "devtools_webhook_manage"
TOOL_WEBHOOK_TEST = "devtools_webhook_test"


class MetaMcpError(Exception):
    def __init__(self, message: str, *, code: str = "MCP_ERROR"):
        super().__init__(message)
        self.code = code


class MetaMcpUnavailable(MetaMcpError):
    def __init__(self, message: str = "Meta Developer Tools temporarily unavailable"):
        super().__init__(message, code="MCP_UNAVAILABLE")


def mcp_enabled() -> bool:
    settings = get_settings()
    return bool(settings.meta_devtools_mcp_enabled or settings.meta_devtools_mcp_mock_mode)


def mock_mode() -> bool:
    return bool(get_settings().meta_devtools_mcp_mock_mode)


def manage_allowed() -> bool:
    settings = get_settings()
    return bool(settings.meta_devtools_mcp_manage_enabled or settings.meta_devtools_mcp_mock_mode)


def _timeout() -> float:
    return max(3.0, float(get_settings().meta_devtools_mcp_timeout_seconds))


def _headers() -> dict[str, str] | None:
    token = (get_settings().meta_devtools_mcp_access_token or "").strip()
    if not token:
        return None
    return {"Authorization": f"Bearer {token}"}


def _text_from_mcp_result(result: Any) -> str:
    parts = [block.text for block in (result.content or []) if getattr(block, "type", "") == "text"]
    return "\n".join(parts).strip()


def _parse_payload(text: str) -> Any:
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some MCP tools return prose; wrap for callers.
        return {"raw": text}


class MetaDeveloperToolsProvider:
    """Encapsulates all Meta DevTools MCP I/O."""

    def __init__(self, *, scenario: str | None = None):
        """scenario is mock-only: healthy|warning|critical|throttled|webhook_missing|compliance_warning|deprecation_warning"""
        self.scenario = scenario or "healthy"

    async def call_tool(self, name: str, arguments: dict | None = None) -> Any:
        settings = get_settings()
        if not mcp_enabled():
            raise MetaMcpUnavailable("Meta Developer Tools MCP is not configured")
        if mock_mode():
            return self._mock_call(name, arguments or {})

        started = time.monotonic()
        try:

            async def _run():
                async with open_mcp_session(
                    settings.meta_devtools_mcp_url,
                    "streamable_http",
                    _headers(),
                ) as session:
                    return await session.call_tool(name, arguments or {})

            result = await asyncio.wait_for(_run(), _timeout())
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.info(
                "meta_mcp_operation tool=%s status=ok duration_ms=%s",
                name,
                duration_ms,
            )
            if getattr(result, "isError", False):
                raise MetaMcpError(_text_from_mcp_result(result) or "MCP tool error", code="MCP_TOOL_ERROR")
            return _parse_payload(_text_from_mcp_result(result))
        except MetaMcpError:
            raise
        except asyncio.TimeoutError as exc:
            logger.warning("meta_mcp_operation tool=%s status=timeout", name)
            raise MetaMcpUnavailable("Meta Developer Tools timed out") from exc
        except Exception as exc:  # noqa: BLE001
            logger.warning("meta_mcp_operation tool=%s status=error type=%s", name, type(exc).__name__)
            raise MetaMcpUnavailable("Meta Developer Tools temporarily unavailable") from exc

    async def list_apps(self) -> Any:
        return await self.call_tool(TOOL_APP_LIST, {})

    async def get_app(self, app_id: str) -> Any:
        return await self.call_tool(TOOL_APP, {"app_id": app_id})

    async def get_app_review(self, app_id: str) -> Any:
        return await self.call_tool(TOOL_APP_REVIEW, {"app_id": app_id})

    async def get_compliance(self, app_id: str) -> Any:
        return await self.call_tool(TOOL_COMPLIANCE, {"app_id": app_id})

    async def get_api_usage(self, app_id: str, *, time_range: str = "24h") -> Any:
        return await self.call_tool(TOOL_API_USAGE, {"app_id": app_id, "time_range": time_range})

    async def list_webhooks(self, app_id: str) -> Any:
        return await self.call_tool(TOOL_WEBHOOK_LIST, {"app_id": app_id})

    async def manage_webhook(self, app_id: str, action: str, payload: dict) -> Any:
        if not manage_allowed():
            raise MetaMcpError("Manage scope / META_DEVTOOLS_MCP_MANAGE_ENABLED required", code="MCP_MANAGE_DENIED")
        body = {"app_id": app_id, "action": action, **payload}
        return await self.call_tool(TOOL_WEBHOOK_MANAGE, body)

    async def test_webhook(self, app_id: str, payload: dict) -> Any:
        if not manage_allowed() and not mock_mode():
            raise MetaMcpError("Manage scope required for webhook test", code="MCP_MANAGE_DENIED")
        body = {"app_id": app_id, **payload}
        return await self.call_tool(TOOL_WEBHOOK_TEST, body)

    def _mock_call(self, name: str, arguments: dict) -> Any:
        scenario = self.scenario
        app_id = arguments.get("app_id") or get_settings().meta_app_id or "mock_app_123"

        if name == TOOL_APP_LIST:
            return {
                "apps": [
                    {"app_id": app_id, "name": "Fast Livery Meta App", "permission": "manage" if manage_allowed() else "read"}
                ]
            }
        if name == TOOL_APP:
            return {
                "app_id": app_id,
                "name": "Fast Livery Meta App",
                "status": "HEALTHY" if scenario != "critical" else "CRITICAL",
                "platforms": ["whatsapp", "instagram"],
            }
        if name == TOOL_APP_REVIEW:
            return {
                "items": [
                    {"permission": "whatsapp_business_messaging", "status": "approved"},
                    {"permission": "instagram_content_publish", "status": "approved"},
                    {
                        "permission": "instagram_manage_messages",
                        "status": "pending" if scenario == "warning" else "approved",
                    },
                ]
            }
        if name == TOOL_COMPLIANCE:
            if scenario in {"compliance_warning", "warning", "critical"}:
                return {
                    "status": "WARNING",
                    "actions": [
                        {
                            "type": "Data Access Renewal",
                            "severity": "14 days",
                            "severity_days": 14,
                            "severity": "Complete Data Access Renewal to keep API access.",
                        }
                    ],
                }
            return {"status": "OK", "actions": []}
        if name == TOOL_API_USAGE:
            pct = {"healthy": 38, "warning": 78, "critical": 94, "throttled": 99}.get(scenario, 38)
            if scenario == "deprecation_warning":
                pct = 42
            status = "THROTTLED" if scenario == "throttled" else ("CRITICAL" if pct >= 90 else ("WARNING" if pct >= 70 else "HEALTHY"))
            return {
                "percentage": pct,
                "call_volume": int(pct * 120),
                "limit": 12000,
                "window": "24h",
                "throttle_status": "throttled" if scenario == "throttled" else "normal",
                "estimated_recovery_minutes": 12 if scenario == "throttled" else None,
                "deprecations": (
                    [{"api": "Graph API", "version": "v21.0", "message": "Version retirement upcoming", "severity_days": 45}]
                    if scenario in {"deprecation_warning", "warning", "critical"}
                    else []
                ),
                "status": status,
            }
        if name == TOOL_WEBHOOK_LIST:
            fields = ["messages", "message_echoes"]
            if scenario != "webhook_missing":
                fields = ["messages", "message_statuses", "message_echoes"]
            return {
                "callback_url": f"{get_settings().backend_url.rstrip('/')}/api/public/whatsapp-cloud/channels/{{channel_id}}/webhook",
                "subscriptions": [
                    {
                        "object": "whatsapp_business_account",
                        "callback_url": f"{get_settings().backend_url.rstrip('/')}/api/public/whatsapp-cloud/channels/example/webhook",
                        "fields": fields,
                        "active": True,
                    }
                ],
                "available_topics": ["messages", "message_statuses", "message_echoes", "account_update"],
            }
        if name == TOOL_WEBHOOK_MANAGE:
            return {"ok": True, "action": arguments.get("action"), "result": "applied"}
        if name == TOOL_WEBHOOK_TEST:
            return {
                "ok": True,
                "sent": True,
                "event_type": arguments.get("field") or "messages",
                "correlation_hint": arguments.get("metaWebhookTestId") or arguments.get("test_id"),
            }
        return {"raw": f"mock unhandled tool {name}"}
