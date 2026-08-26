"""Consolidate Meta DevTools MCP into OpenLivery DTOs (platform health)."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import MetaWebhookTest, User, now_utc
from .meta_devtools_mcp import (
    MetaDeveloperToolsProvider,
    MetaMcpError,
    MetaMcpUnavailable,
    manage_allowed,
    mcp_enabled,
    mock_mode,
)

logger = logging.getLogger("openlivery.meta_platform_health")

# WhatsApp Cloud webhook fields OpenLivery expects (do not invent message quotas).
EXPECTED_WHATSAPP_WEBHOOK_FIELDS = ("messages", "message_statuses")

_cache: dict[str, tuple[float, Any]] = {}
_inflight_tests: dict[str, dict] = {}


def _status_rank(status: str) -> int:
    order = {
        "HEALTHY": 0,
        "OK": 0,
        "INFO": 1,
        "WARNING": 2,
        "THROTTLED": 3,
        "CRITICAL": 4,
        "UNAVAILABLE": 5,
        "UNKNOWN": 6,
    }
    return order.get(status, 6)


def worst_status(*statuses: str) -> str:
    if not statuses:
        return "UNKNOWN"
    return max(statuses, key=_status_rank)


def normalize_status(value: Any, *, percentage: float | None = None) -> str:
    if value is None and percentage is not None:
        settings = get_settings()
        if percentage >= settings.meta_api_critical_threshold:
            return "CRITICAL"
        if percentage >= settings.meta_api_warning_threshold:
            return "WARNING"
        return "HEALTHY"
    text = str(value or "").strip().upper()
    aliases = {
        "OK": "HEALTHY",
        "HEALTHY": "HEALTHY",
        "NORMAL": "HEALTHY",
        "WARNING": "WARNING",
        "WARN": "WARNING",
        "CRITICAL": "CRITICAL",
        "ERROR": "CRITICAL",
        "THROTTLED": "THROTTLED",
        "UNAVAILABLE": "UNAVAILABLE",
        "UNKNOWN": "UNKNOWN",
        "PENDING": "WARNING",
        "ACTION_REQUIRED": "WARNING",
        "REJECTED": "CRITICAL",
        "APPROVED": "HEALTHY",
    }
    if text in aliases:
        return aliases[text]
    if percentage is not None:
        return normalize_status(None, percentage=percentage)
    return "UNKNOWN"


def _cache_get(key: str) -> Any | None:
    row = _cache.get(key)
    if not row:
        return None
    expires, value = row
    if time.time() > expires:
        _cache.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any, ttl: int) -> None:
    _cache[key] = (time.time() + max(1, ttl), value)


def clear_meta_cache() -> None:
    _cache.clear()


def resolve_app_id(raw: Any, fallback: str) -> str:
    if isinstance(raw, dict):
        apps = raw.get("apps") or raw.get("data") or []
        if apps and isinstance(apps[0], dict):
            return str(apps[0].get("app_id") or apps[0].get("id") or fallback)
    return fallback


class MetaPlatformHealthService:
    def __init__(self, provider: MetaDeveloperToolsProvider | None = None):
        self.provider = provider or MetaDeveloperToolsProvider()

    def status_payload(self) -> dict:
        settings = get_settings()
        return {
            "enabled": mcp_enabled(),
            "mock_mode": mock_mode(),
            "manage_enabled": manage_allowed(),
            "url_configured": bool(settings.meta_devtools_mcp_url),
            "token_configured": bool(settings.meta_devtools_mcp_access_token),
            "meta_app_id": settings.meta_app_id or None,
            "message": None
            if mcp_enabled()
            else "Advanced Meta diagnostics are not configured (META_DEVTOOLS_MCP_ENABLED or MOCK).",
        }

    async def _ensure_app_id(self) -> str:
        settings = get_settings()
        if settings.meta_app_id:
            return settings.meta_app_id
        listed = await self.provider.list_apps()
        return resolve_app_id(listed, "unknown")

    async def get_health(self, *, time_range: str = "24h", force: bool = False) -> dict:
        if not mcp_enabled():
            return {
                "overall_status": "UNAVAILABLE",
                "enabled": False,
                "mock_mode": False,
                "fetched_at": now_utc().isoformat(),
                "message": "Advanced Meta diagnostics are not configured",
                "app": {"status": "UNAVAILABLE"},
                "api_usage": {"status": "UNAVAILABLE"},
                "rate_limits": {"status": "UNAVAILABLE"},
                "webhooks": {"status": "UNAVAILABLE"},
                "app_review": {"status": "UNAVAILABLE"},
                "compliance": {"status": "UNAVAILABLE"},
                "deprecations": {"status": "UNAVAILABLE", "count": 0, "items": []},
                "alerts": [],
            }

        cache_key = f"health:{time_range}:{self.provider.scenario}"
        if not force:
            cached = _cache_get(cache_key)
            if cached:
                return cached

        settings = get_settings()
        try:
            app_id = await self._ensure_app_id()
            app_p, usage_p, review_p, compliance_p, hooks_p = await asyncio.gather(
                self.provider.get_app(app_id),
                self.provider.get_api_usage(app_id, time_range=time_range),
                self.provider.get_app_review(app_id),
                self.provider.get_compliance(app_id),
                self.provider.list_webhooks(app_id),
                return_exceptions=True,
            )
        except MetaMcpUnavailable as exc:
            return {
                "overall_status": "UNAVAILABLE",
                "enabled": True,
                "mock_mode": mock_mode(),
                "fetched_at": now_utc().isoformat(),
                "message": str(exc),
                "app": {"status": "UNAVAILABLE"},
                "api_usage": {"status": "UNAVAILABLE"},
                "rate_limits": {"status": "UNAVAILABLE"},
                "webhooks": {"status": "UNAVAILABLE"},
                "app_review": {"status": "UNAVAILABLE"},
                "compliance": {"status": "UNAVAILABLE"},
                "deprecations": {"status": "UNAVAILABLE", "count": 0, "items": []},
                "alerts": [{"level": "WARNING", "code": "MCP_UNAVAILABLE", "message": str(exc)}],
            }

        def _safe(result: Any, label: str) -> tuple[Any, str | None]:
            if isinstance(result, Exception):
                logger.warning("meta_health_partial label=%s error=%s", label, type(result).__name__)
                return None, str(result)
            return result, None

        app, app_err = _safe(app_p, "app")
        usage, usage_err = _safe(usage_p, "usage")
        review, review_err = _safe(review_p, "review")
        compliance, compliance_err = _safe(compliance_p, "compliance")
        hooks, hooks_err = _safe(hooks_p, "webhooks")

        usage = usage if isinstance(usage, dict) else {}
        percentage = usage.get("percentage")
        try:
            percentage_f = float(percentage) if percentage is not None else None
        except (TypeError, ValueError):
            percentage_f = None

        api_status = normalize_status(usage.get("status"), percentage=percentage_f)
        throttle = str(usage.get("throttle_status") or "").lower()
        if throttle == "throttled":
            api_status = "THROTTLED"
        rate_status = api_status

        dep_items = usage.get("deprecations") or []
        if not isinstance(dep_items, list):
            dep_items = []
        dep_status = "WARNING" if dep_items else "HEALTHY"

        app_status = normalize_status((app or {}).get("status") if isinstance(app, dict) else None)
        if app_err:
            app_status = "UNAVAILABLE"

        review_items = []
        if isinstance(review, dict):
            review_items = review.get("items") or review.get("permissions") or []
        review_statuses = [normalize_status(i.get("status")) for i in review_items if isinstance(i, dict)]
        review_status = worst_status(*(review_statuses or ["UNKNOWN"]))
        if review_err:
            review_status = "UNAVAILABLE"

        compliance = compliance if isinstance(compliance, dict) else {}
        compliance_status = normalize_status(compliance.get("status"))
        actions = compliance.get("actions") or []
        if actions and compliance_status == "HEALTHY":
            compliance_status = "WARNING"
        if compliance_err:
            compliance_status = "UNAVAILABLE"

        webhook_diff = self.diff_webhooks(hooks if isinstance(hooks, dict) else {})
        webhook_status = "HEALTHY" if not webhook_diff["missing"] else "WARNING"
        if hooks_err:
            webhook_status = "UNAVAILABLE"

        overall = worst_status(app_status, api_status, rate_status, webhook_status, review_status, compliance_status, dep_status)

        alerts = []
        if percentage_f is not None and percentage_f >= settings.meta_api_warning_threshold:
            alerts.append(
                {
                    "level": "CRITICAL" if percentage_f >= settings.meta_api_critical_threshold else "WARNING",
                    "code": "API_USAGE",
                    "message": f"Meta API usage at {percentage_f:.0f}% (not a WhatsApp message quota).",
                }
            )
        if rate_status == "THROTTLED":
            alerts.append({"level": "CRITICAL", "code": "THROTTLED", "message": "Meta API throttling detected."})
        if webhook_diff["missing"]:
            alerts.append(
                {
                    "level": "WARNING",
                    "code": "WEBHOOK_MISSING",
                    "message": f"Missing webhook fields: {', '.join(webhook_diff['missing'])}",
                }
            )
        if compliance_status == "WARNING":
            alerts.append({"level": "WARNING", "code": "COMPLIANCE", "message": "Compliance action required."})
        if dep_items:
            alerts.append(
                {
                    "level": "WARNING",
                    "code": "DEPRECATION",
                    "message": f"{len(dep_items)} API deprecation warning(s).",
                }
            )

        payload = {
            "overall_status": overall,
            "enabled": True,
            "mock_mode": mock_mode(),
            "app_id": await self._ensure_app_id() if not isinstance(app_p, Exception) else settings.meta_app_id,
            "fetched_at": now_utc().isoformat(),
            "time_range": time_range,
            "message": None,
            "app": {"status": app_status, "detail": app if isinstance(app, dict) else None, "error": app_err},
            "api_usage": {
                "status": api_status,
                "percentage": percentage_f,
                "call_volume": usage.get("call_volume"),
                "limit": usage.get("limit"),
                "window": usage.get("window") or time_range,
                "label": "Meta API usage (Graph call volume — not WhatsApp message quota)",
                "error": usage_err,
            },
            "rate_limits": {
                "status": rate_status,
                "throttle_status": usage.get("throttle_status"),
                "estimated_recovery_minutes": usage.get("estimated_recovery_minutes"),
                "error": usage_err,
            },
            "webhooks": {
                "status": webhook_status,
                "missing": webhook_diff["missing"],
                "present": webhook_diff["present"],
                "extra": webhook_diff["extra"],
                "error": hooks_err,
            },
            "app_review": {
                "status": review_status,
                "items": [
                    {"permission": i.get("permission") or i.get("name"), "status": normalize_status(i.get("status"))}
                    for i in review_items
                    if isinstance(i, dict)
                ],
                "error": review_err,
            },
            "compliance": {
                "status": compliance_status,
                "actions": actions if isinstance(actions, list) else [],
                "error": compliance_err,
            },
            "deprecations": {
                "status": dep_status,
                "count": len(dep_items),
                "items": dep_items,
            },
            "alerts": alerts,
            "manage_enabled": manage_allowed(),
        }
        _cache_set(cache_key, payload, settings.meta_mcp_cache_ttl_seconds)
        return payload

    def diff_webhooks(self, webhook_payload: dict) -> dict:
        present: set[str] = set()
        subscriptions = webhook_payload.get("subscriptions") or webhook_payload.get("data") or []
        if isinstance(subscriptions, list):
            for sub in subscriptions:
                if not isinstance(sub, dict):
                    continue
                fields = sub.get("fields") or []
                if isinstance(fields, list):
                    present.update(str(f) for f in fields)
        expected = set(EXPECTED_WHATSAPP_WEBHOOK_FIELDS)
        return {
            "expected": sorted(expected),
            "present": sorted(present),
            "missing": sorted(expected - present),
            "extra": sorted(present - expected),
            "subscriptions": subscriptions if isinstance(subscriptions, list) else [],
            "callback_url": webhook_payload.get("callback_url"),
        }

    async def inspect_webhooks(self, *, force: bool = False) -> dict:
        if not mcp_enabled():
            raise MetaMcpUnavailable("Meta Developer Tools MCP is not configured")
        cache_key = "webhooks"
        if not force:
            cached = _cache_get(cache_key)
            if cached:
                return cached
        app_id = await self._ensure_app_id()
        raw = await self.provider.list_webhooks(app_id)
        raw = raw if isinstance(raw, dict) else {"raw": raw}
        diff = self.diff_webhooks(raw)
        out = {
            "app_id": app_id,
            "fetched_at": now_utc().isoformat(),
            "manage_enabled": manage_allowed(),
            **diff,
            "raw_summary": {
                "available_topics": raw.get("available_topics"),
                "callback_url": raw.get("callback_url"),
            },
        }
        _cache_set(cache_key, out, get_settings().meta_mcp_cache_ttl_seconds)
        return out

    async def run_diagnostics(self) -> dict:
        health = await self.get_health(force=True)
        checks = [
            {"name": "META_APP", "status": health["app"]["status"], "message": health["app"].get("error")},
            {
                "name": "API_USAGE",
                "status": health["api_usage"]["status"],
                "message": None
                if health["api_usage"].get("percentage") is None
                else f"{health['api_usage']['percentage']}% Graph API usage",
            },
            {"name": "RATE_LIMITS", "status": health["rate_limits"]["status"]},
            {
                "name": "WEBHOOK",
                "status": health["webhooks"]["status"],
                "message": (
                    f"Missing: {', '.join(health['webhooks']['missing'])}"
                    if health["webhooks"].get("missing")
                    else None
                ),
            },
            {"name": "APP_REVIEW", "status": health["app_review"]["status"]},
            {"name": "COMPLIANCE", "status": health["compliance"]["status"]},
            {
                "name": "DEPRECATIONS",
                "status": health["deprecations"]["status"],
                "message": f"{health['deprecations']['count']} warning(s)"
                if health["deprecations"]["count"]
                else None,
            },
        ]
        ok = sum(1 for c in checks if c["status"] in {"HEALTHY", "OK"})
        warn = sum(1 for c in checks if c["status"] in {"WARNING", "THROTTLED"})
        return {
            "status": health["overall_status"],
            "checks": checks,
            "summary": {"total": len(checks), "healthy": ok, "attention": warn},
            "health": health,
        }

    async def start_webhook_test(self, db: Session, user: User, *, field: str = "messages") -> dict:
        if not mcp_enabled():
            raise MetaMcpUnavailable("Meta Developer Tools MCP is not configured")
        test_id = uuid.uuid4().hex
        app_id = await self._ensure_app_id()
        row = MetaWebhookTest(
            agency_id=user.agency_id,
            requested_by_user_id=user.id,
            test_id=test_id,
            app_id=app_id,
            event_type=field,
            status="requested",
            requested_at=now_utc(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        _inflight_tests[test_id] = {"agency_id": str(user.agency_id), "requested_at": time.time()}

        meta_sent = False
        meta_error = None
        try:
            await self.provider.test_webhook(
                app_id,
                {"field": field, "metaWebhookTestId": test_id, "test_id": test_id},
            )
            meta_sent = True
            row.status = "sent"
            # Mock path: simulate inbound receipt shortly after send.
            if mock_mode():
                row.received_at = now_utc()
                row.status = "received"
                row.latency_ms = 50
                mark_webhook_test_received(test_id, event_type=field)
        except MetaMcpError as exc:
            meta_error = str(exc)
            row.status = "failed"
            row.error = str(exc)
        db.commit()
        db.refresh(row)
        return {
            "test_id": test_id,
            "status": row.status,
            "meta_request_accepted": meta_sent,
            "openlivery_received": row.received_at is not None,
            "latency_ms": row.latency_ms,
            "event_type": field,
            "error": meta_error,
            "steps": {
                "meta_received_request": meta_sent,
                "event_sent": meta_sent,
                "openlivery_received_event": row.received_at is not None,
                "processing_ok": row.status in {"received", "processed"},
            },
        }

    async def preview_webhook_repair(self) -> dict:
        inspected = await self.inspect_webhooks(force=True)
        missing = inspected.get("missing") or []
        return {
            "manage_enabled": manage_allowed(),
            "changes": [{"op": "add_field", "field": f} for f in missing],
            "missing": missing,
            "extra_untouched": inspected.get("extra") or [],
            "note": "Extra subscriptions are never removed automatically.",
        }

    async def apply_webhook_repair(self, *, confirm: bool, db: Session, user: User) -> dict:
        if not confirm:
            raise MetaMcpError("Repair requires confirm=true", code="CONFIRM_REQUIRED")
        if not manage_allowed():
            raise MetaMcpError("Administrative Meta Manage permission required", code="MCP_MANAGE_DENIED")
        preview = await self.preview_webhook_repair()
        app_id = await self._ensure_app_id()
        applied = []
        for change in preview["changes"]:
            result = await self.provider.manage_webhook(
                app_id,
                "subscribe",
                {"field": change["field"], "object": "whatsapp_business_account"},
            )
            applied.append({"change": change, "result": result})
            logger.info(
                "meta_mcp_operation tool=webhook_repair status=ok user=%s field=%s",
                user.id,
                change["field"],
            )
        clear_meta_cache()
        after = await self.inspect_webhooks(force=True)
        return {"applied": applied, "after": after, "preview": preview}


def mark_webhook_test_received(test_id: str, *, event_type: str | None = None) -> bool:
    """Called from webhook receiver when a correlated test event arrives."""
    meta = _inflight_tests.get(test_id)
    if not meta:
        return False
    meta["received"] = True
    meta["event_type"] = event_type
    meta["received_at"] = time.time()
    return True


def list_recent_webhook_tests(db: Session, agency_id: uuid.UUID, *, limit: int = 10) -> list[MetaWebhookTest]:
    return (
        db.query(MetaWebhookTest)
        .filter(MetaWebhookTest.agency_id == agency_id)
        .order_by(MetaWebhookTest.created_at.desc())
        .limit(limit)
        .all()
    )
