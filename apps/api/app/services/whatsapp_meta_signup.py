"""Meta Embedded Signup / OAuth helpers for WhatsApp Cloud onboarding.

Real Embedded Signup requires META_APP_ID + META_WHATSAPP_CONFIG_ID and a
public redirect. When META_MOCK_MODE=true, completion synthesizes a channel
without calling Meta (same persistence path as the real flow).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from ..config import get_settings
from ..security import decrypt_secret, encrypt_secret


STATE_TTL_SECONDS = 60 * 15
GRAPH_TIMEOUT = 30


def managed_meta_configured() -> bool:
    settings = get_settings()
    return bool(settings.meta_app_id and (settings.meta_mock_mode or settings.meta_whatsapp_config_id or settings.meta_app_secret))


def signup_options() -> dict:
    settings = get_settings()
    return {
        "managed_available": managed_meta_configured(),
        "mock_mode": settings.meta_mock_mode,
        "meta_app_id": settings.meta_app_id or None,
        "meta_config_id": settings.meta_whatsapp_config_id or None,
        "graph_version": settings.meta_graph_base_url.rstrip("/").split("/")[-1],
        "blocked_reason": None
        if managed_meta_configured()
        else "BLOCKED_BY_EXTERNAL_CONFIGURATION: set META_APP_ID and META_WHATSAPP_CONFIG_ID (or META_MOCK_MODE=true).",
    }


def _state_secret() -> bytes:
    return get_settings().secret_key.encode()


def create_signup_state(*, agency_id: str, client_id: str, user_id: str) -> str:
    payload = {
        "agency_id": agency_id,
        "client_id": client_id,
        "user_id": user_id,
        "nonce": secrets.token_urlsafe(16),
        "exp": int(time.time()) + STATE_TTL_SECONDS,
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    sig = hmac.new(_state_secret(), body.encode(), hashlib.sha256).hexdigest()
    token = f"{body}|{sig}"
    return encrypt_secret(token)


def parse_signup_state(state_token: str) -> dict:
    try:
        raw = decrypt_secret(state_token)
        body, sig = raw.rsplit("|", 1)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc
    expected = hmac.new(_state_secret(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=400, detail="Invalid OAuth state signature")
    payload = json.loads(body)
    if int(payload.get("exp") or 0) < int(time.time()):
        raise HTTPException(status_code=400, detail="OAuth state expired")
    return payload


def build_embedded_signup_url(state: str) -> str | None:
    """Optional redirect-style entry; primary path uses FB JS SDK on the client."""
    settings = get_settings()
    if not settings.meta_app_id:
        return None
    redirect = f"{settings.frontend_url.rstrip('/')}{settings.meta_oauth_redirect_path}"
    query = urlencode(
        {
            "client_id": settings.meta_app_id,
            "redirect_uri": redirect,
            "state": state,
            "response_type": "code",
            "config_id": settings.meta_whatsapp_config_id or "",
            "override_default_response_type": "true",
        }
    )
    return f"https://www.facebook.com/{settings.meta_graph_base_url.rstrip('/').split('/')[-1]}/dialog/oauth?{query}"


async def exchange_code_for_token(code: str) -> str:
    settings = get_settings()
    if settings.meta_mock_mode:
        return "mock-access-token"
    if not settings.meta_app_id or not settings.meta_app_secret:
        raise HTTPException(
            status_code=503,
            detail="BLOCKED_BY_EXTERNAL_CONFIGURATION: META_APP_ID and META_APP_SECRET required",
        )
    redirect = f"{settings.frontend_url.rstrip('/')}{settings.meta_oauth_redirect_path}"
    url = f"{settings.meta_graph_base_url.rstrip('/')}/oauth/access_token"
    try:
        async with httpx.AsyncClient(timeout=GRAPH_TIMEOUT) as client:
            response = await client.get(
                url,
                params={
                    "client_id": settings.meta_app_id,
                    "client_secret": settings.meta_app_secret,
                    "redirect_uri": redirect,
                    "code": code,
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not reach the Meta API.") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Could not exchange the Meta authorization code.")
    data = response.json()
    token = data.get("access_token")
    if not token:
        raise HTTPException(status_code=502, detail="Meta did not return an access token.")
    return token


async def discover_whatsapp_assets(access_token: str) -> dict:
    """Fetch WABA + first phone number when Meta grants the token."""
    settings = get_settings()
    if settings.meta_mock_mode or access_token == "mock-access-token":
        return {
            "waba_id": "mock-waba-001",
            "phone_number_id": "mock-phone-001",
            "phone_number": "+57 300 000 0000",
            "display_name": "Mock Business",
            "steps": [
                {"id": "auth", "label": "Meta authorization", "done": True},
                {"id": "waba", "label": "WhatsApp account found", "done": True},
                {"id": "phone", "label": "Phone number detected", "done": True},
                {"id": "permissions", "label": "Permissions validated", "done": True},
                {"id": "credentials", "label": "Credentials stored", "done": True},
                {"id": "webhook", "label": "Webhook ready", "done": True},
            ],
        }

    url = f"{settings.meta_graph_base_url.rstrip('/')}/me/businesses"
    try:
        async with httpx.AsyncClient(timeout=GRAPH_TIMEOUT) as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"fields": "id,name,owned_whatsapp_business_accounts{id,name,phone_numbers{id,display_phone_number,verified_name}}"},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not reach the Meta API.") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Could not list WhatsApp assets from Meta.")

    data = response.json()
    businesses = data.get("data") or []
    for business in businesses:
        for waba in (business.get("owned_whatsapp_business_accounts") or {}).get("data") or []:
            phones = (waba.get("phone_numbers") or {}).get("data") or []
            if not phones:
                continue
            phone = phones[0]
            return {
                "waba_id": waba.get("id"),
                "phone_number_id": phone.get("id"),
                "phone_number": phone.get("display_phone_number"),
                "display_name": phone.get("verified_name") or business.get("name"),
                "steps": [
                    {"id": "auth", "label": "Meta authorization", "done": True},
                    {"id": "waba", "label": "WhatsApp account found", "done": True},
                    {"id": "phone", "label": "Phone number detected", "done": True},
                    {"id": "permissions", "label": "Permissions validated", "done": True},
                    {"id": "credentials", "label": "Credentials stored", "done": False},
                    {"id": "webhook", "label": "Webhook ready", "done": False},
                ],
            }
    raise HTTPException(
        status_code=400,
        detail="No WhatsApp Business phone number was returned by Meta for this authorization.",
    )


def resolve_app_secret_for_channel(channel) -> str | None:
    """Prefer channel BYO secret; fall back to platform META_APP_SECRET."""
    if channel.encrypted_app_secret:
        return decrypt_secret(channel.encrypted_app_secret)
    settings = get_settings()
    return settings.meta_app_secret or None
