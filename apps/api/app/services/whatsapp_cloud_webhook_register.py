"""Register WhatsApp Cloud webhook overrides via the Meta Graph API.

Mirrors the Vocero pattern: prefer a phone-number-level override so reconnects
do not wipe an agency-level WABA callback. Never fail a channel save/connect
because Meta rejected the registration — return a structured result instead.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, Literal
from urllib.parse import urlparse

import httpx

from ..config import get_settings

logger = logging.getLogger("openlivery.whatsapp_cloud_webhook")

GRAPH_TIMEOUT = 30

WebhookCode = Literal[
    "registered",
    "skipped_waba_override",
    "mock",
    "invalid_token",
    "missing_permission",
    "meta_unavailable",
    "meta_error",
]


@dataclass
class WebhookRegistrationResult:
    ok: bool
    code: WebhookCode
    message: str
    host: str | None = None
    app_without_webhook: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _graph_base() -> str:
    return get_settings().meta_graph_base_url.rstrip("/")


def _path_of(url: str) -> str:
    return urlparse(url).path.rstrip("/") or "/"


def _host_of(url: str) -> str:
    return urlparse(url).netloc or ""


def _same_webhook_path(url: str, path: str) -> bool:
    return _path_of(url) == path.rstrip("/") or _path_of(url) == path


async def _graph_json(
    method: str,
    path: str,
    token: str,
    *,
    json_body: dict | None = None,
) -> tuple[int, dict | list | None, str | None]:
    url = f"{_graph_base()}/{path.lstrip('/')}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(timeout=GRAPH_TIMEOUT) as client:
            response = await client.request(method, url, headers=headers, json=json_body)
    except httpx.HTTPError as exc:
        return 0, None, str(exc)
    try:
        payload = response.json()
    except ValueError:
        payload = None
    error_message = None
    if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
        error_message = payload["error"].get("message") or payload["error"].get("error_user_msg")
    return response.status_code, payload if isinstance(payload, (dict, list)) else None, error_message


def _classify_error(status: int, message: str | None, context: str) -> WebhookRegistrationResult:
    detail = message or "Meta rejected the request"
    if status in {0} or status >= 500:
        return WebhookRegistrationResult(
            ok=False,
            code="meta_unavailable",
            message=f"{context}: Meta is temporarily unavailable",
        )
    lowered = detail.lower()
    if status in {401, 403} or "access token" in lowered or "oauth" in lowered:
        return WebhookRegistrationResult(ok=False, code="invalid_token", message=f"{context}: {detail}")
    if "permission" in lowered or "whatsapp_business_management" in lowered:
        return WebhookRegistrationResult(
            ok=False,
            code="missing_permission",
            message=(
                f"{context}: token needs whatsapp_business_management "
                f"(and messaging) to register the webhook automatically. {detail}"
            ),
        )
    return WebhookRegistrationResult(ok=False, code="meta_error", message=f"{context}: {detail}")


async def _waba_override_uri(waba_id: str, token: str) -> tuple[str | None, bool]:
    """Return (override_uri_or_None, probe_ok).

    probe_ok=False means subscribed_apps could not be read; caller may subscribe
    best-effort without treating a foreign override as present.
    """
    status, payload, _ = await _graph_json("GET", f"{waba_id}/subscribed_apps", token)
    if status >= 400 or not isinstance(payload, dict):
        logger.warning("subscribed_apps probe failed waba_id=%s status=%s", waba_id, status)
        return None, False
    for app in payload.get("data") or []:
        if not isinstance(app, dict):
            continue
        uri = app.get("override_callback_uri")
        if isinstance(uri, str) and uri.strip():
            return uri.strip(), True
    return None, True


async def register_webhook_for_number(
    *,
    waba_id: str | None,
    phone_number_id: str,
    access_token: str,
    webhook_url: str,
    verify_token: str,
) -> WebhookRegistrationResult:
    settings = get_settings()
    if (
        settings.meta_mock_mode
        or access_token == "mock-access-token"
        or phone_number_id.startswith("mock-")
    ):
        return WebhookRegistrationResult(
            ok=True,
            code="mock",
            message="Mock mode: webhook registration skipped (assume configured).",
        )

    if not phone_number_id.strip() or not verify_token.strip() or not webhook_url.strip():
        return WebhookRegistrationResult(
            ok=False,
            code="meta_error",
            message="Phone number ID, webhook URL and verify token are required",
        )

    own_path = _path_of(webhook_url)

    if waba_id and waba_id.strip():
        override, probe_ok = await _waba_override_uri(waba_id.strip(), access_token)
        if override and not _same_webhook_path(override, own_path):
            host = _host_of(override)
            logger.info(
                "waba %s already routes webhooks to %s; skipping phone override",
                waba_id,
                host,
            )
            await unregister_webhook_for_number(
                phone_number_id=phone_number_id,
                access_token=access_token,
                webhook_path=own_path,
            )
            return WebhookRegistrationResult(
                ok=True,
                code="skipped_waba_override",
                message=(
                    f"WABA already routes webhooks to {host}. "
                    "Phone-level override was not set so that destination stays active."
                ),
                host=host or None,
            )
        if probe_ok and override is None:
            # Empty POST subscribes the app. Do NOT call this when probe failed:
            # Meta documents the same call as deleting a WABA alternate callback.
            status, _payload, err = await _graph_json(
                "POST", f"{waba_id.strip()}/subscribed_apps", access_token
            )
            if status >= 400:
                return _classify_error(status, err, "Could not subscribe the app to the WABA")
        elif not probe_ok:
            logger.warning(
                "skipping WABA subscribed_apps POST because probe failed (avoids wiping overrides) waba_id=%s",
                waba_id,
            )
    status, _payload, err = await _graph_json(
        "POST",
        phone_number_id,
        access_token,
        json_body={
            "webhook_configuration": {
                "override_callback_uri": webhook_url,
                "verify_token": verify_token,
            }
        },
    )
    if status >= 400:
        return _classify_error(status, err, "Meta rejected the webhook override")

    status, payload, err = await _graph_json(
        "GET",
        f"{phone_number_id}?fields=webhook_configuration",
        access_token,
    )
    if status >= 400 or not isinstance(payload, dict):
        return _classify_error(status, err, "Could not confirm webhook on the number")

    config = payload.get("webhook_configuration") or {}
    phone_uri = config.get("phone_number") if isinstance(config, dict) else None
    app_uri = config.get("application") if isinstance(config, dict) else None
    if phone_uri != webhook_url:
        return WebhookRegistrationResult(
            ok=False,
            code="meta_error",
            message=(
                "Meta accepted the webhook but does not confirm it on the number yet. "
                "Retry in a few minutes."
            ),
        )
    return WebhookRegistrationResult(
        ok=True,
        code="registered",
        message="Webhook registered on the phone number via Meta Graph API.",
        app_without_webhook=not bool(app_uri),
    )


async def unregister_webhook_for_number(
    *,
    phone_number_id: str,
    access_token: str,
    webhook_path: str,
) -> None:
    """Best-effort clear of our phone-level override on disconnect."""
    settings = get_settings()
    if (
        settings.meta_mock_mode
        or access_token == "mock-access-token"
        or phone_number_id.startswith("mock-")
    ):
        return
    try:
        status, payload, _ = await _graph_json(
            "GET",
            f"{phone_number_id}?fields=webhook_configuration",
            access_token,
        )
        if status >= 400 or not isinstance(payload, dict):
            return
        config = payload.get("webhook_configuration") or {}
        actual = config.get("phone_number") if isinstance(config, dict) else None
        if not isinstance(actual, str) or not _same_webhook_path(actual, webhook_path):
            return
        await _graph_json(
            "POST",
            phone_number_id,
            access_token,
            json_body={"webhook_configuration": {"override_callback_uri": ""}},
        )
    except Exception:  # noqa: BLE001 — disconnect must not fail on Meta
        logger.warning("failed to clear webhook override for phone_number_id=%s", phone_number_id, exc_info=True)
