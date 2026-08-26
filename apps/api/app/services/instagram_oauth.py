"""Facebook Login → Instagram Business Account discovery for publishing."""

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
from .instagram_graph import mock_enabled


STATE_TTL_SECONDS = 60 * 15
# Scopes for Instagram API with Facebook Login (Content Publishing).
# Prefer business_* names when the Meta App uses Instagram API product;
# keep classic names for broader compatibility during App Review transitions.
DEFAULT_SCOPES = [
    "pages_show_list",
    "pages_read_engagement",
    "instagram_basic",
    "instagram_content_publish",
    "business_management",
]


def oauth_options() -> dict:
    settings = get_settings()
    configured = bool(settings.meta_app_id and (settings.meta_app_secret or mock_enabled()))
    return {
        "oauth_available": configured or mock_enabled(),
        "mock_mode": mock_enabled(),
        "meta_app_id": settings.meta_app_id or None,
        "graph_version": settings.meta_graph_base_url.rstrip("/").split("/")[-1],
        "scopes": DEFAULT_SCOPES,
        "redirect_path": settings.instagram_oauth_redirect_path,
        "blocked_reason": None
        if (configured or mock_enabled())
        else "BLOCKED_BY_EXTERNAL_CONFIGURATION: set META_APP_ID + META_APP_SECRET (or INSTAGRAM_PUBLISHING_MOCK_MODE=true).",
    }


def _state_secret() -> bytes:
    return get_settings().secret_key.encode()


def create_oauth_state(*, agency_id: str, client_id: str, user_id: str) -> str:
    payload = {
        "agency_id": agency_id,
        "client_id": client_id,
        "user_id": user_id,
        "purpose": "instagram_publish",
        "nonce": secrets.token_urlsafe(16),
        "exp": int(time.time()) + STATE_TTL_SECONDS,
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    sig = hmac.new(_state_secret(), body.encode(), hashlib.sha256).hexdigest()
    return encrypt_secret(f"{body}|{sig}")


def parse_oauth_state(state_token: str) -> dict:
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
    if payload.get("purpose") != "instagram_publish":
        raise HTTPException(status_code=400, detail="Invalid OAuth purpose")
    return payload


def build_oauth_dialog_url(state: str) -> str | None:
    settings = get_settings()
    if not settings.meta_app_id:
        return None
    redirect = f"{settings.frontend_url.rstrip('/')}{settings.instagram_oauth_redirect_path}"
    version = settings.meta_graph_base_url.rstrip("/").split("/")[-1]
    query = urlencode(
        {
            "client_id": settings.meta_app_id,
            "redirect_uri": redirect,
            "state": state,
            "response_type": "code",
            "scope": ",".join(DEFAULT_SCOPES),
        }
    )
    return f"https://www.facebook.com/{version}/dialog/oauth?{query}"


async def exchange_code_for_token(code: str) -> dict:
    settings = get_settings()
    if mock_enabled():
        return {"access_token": f"mock_user_token_{secrets.token_hex(8)}", "expires_in": 3600}
    redirect = f"{settings.frontend_url.rstrip('/')}{settings.instagram_oauth_redirect_path}"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{settings.meta_graph_base_url.rstrip('/')}/oauth/access_token",
            params={
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "redirect_uri": redirect,
                "code": code,
            },
        )
    payload = response.json()
    if response.status_code >= 400 or not payload.get("access_token"):
        raise HTTPException(status_code=400, detail=payload.get("error", {}).get("message") or "Token exchange failed")
    return payload


async def exchange_long_lived_user_token(short_token: str) -> dict:
    settings = get_settings()
    if mock_enabled():
        return {"access_token": short_token, "expires_in": 60 * 60 * 24 * 60}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{settings.meta_graph_base_url.rstrip('/')}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "fb_exchange_token": short_token,
            },
        )
    payload = response.json()
    if response.status_code >= 400 or not payload.get("access_token"):
        # Keep short-lived token if exchange fails.
        return {"access_token": short_token, "expires_in": None}
    return payload


async def discover_instagram_accounts(user_access_token: str) -> list[dict]:
    """Return IG professional accounts linked to Pages the user manages."""
    if mock_enabled():
        return [
            {
                "page_id": "mock_page_1",
                "page_name": "Mock Business Page",
                "instagram_user_id": "mock_ig_17841400000000000",
                "username": "mock_brand",
                "display_name": "Mock Brand",
                "page_access_token": f"mock_page_token_{secrets.token_hex(6)}",
            }
        ]
    settings = get_settings()
    accounts: list[dict] = []
    async with httpx.AsyncClient(timeout=30) as client:
        pages_resp = await client.get(
            f"{settings.meta_graph_base_url.rstrip('/')}/me/accounts",
            params={
                "fields": "id,name,access_token,instagram_business_account{id,username,name}",
                "access_token": user_access_token,
            },
        )
        pages_payload = pages_resp.json()
        if pages_resp.status_code >= 400:
            raise HTTPException(
                status_code=400,
                detail=(pages_payload.get("error") or {}).get("message") or "Could not list Pages",
            )
        for page in pages_payload.get("data") or []:
            ig = page.get("instagram_business_account") or {}
            if not ig.get("id"):
                continue
            accounts.append(
                {
                    "page_id": page.get("id"),
                    "page_name": page.get("name"),
                    "instagram_user_id": ig.get("id"),
                    "username": ig.get("username"),
                    "display_name": ig.get("name") or ig.get("username"),
                    "page_access_token": page.get("access_token"),
                }
            )
    return accounts


def has_publish_permission(scopes: list | None) -> bool:
    granted = {str(s).lower() for s in (scopes or [])}
    return bool(
        granted
        & {
            "instagram_content_publish",
            "instagram_business_content_publish",
        }
    ) or mock_enabled()
