"""OAuth 2.0 for LinkedIn personal-profile publishing."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from ...config import get_settings
from ...security import decrypt_secret, encrypt_secret


STATE_TTL_SECONDS = 60 * 15
DEFAULT_SCOPES = ["openid", "profile", "w_member_social"]


def mock_enabled() -> bool:
    return bool(get_settings().linkedin_mock_mode)


def oauth_options() -> dict:
    settings = get_settings()
    configured = bool(settings.linkedin_client_id and settings.linkedin_client_secret)
    available = configured or mock_enabled()
    return {
        "oauth_available": available,
        "mock_mode": mock_enabled(),
        "client_id": settings.linkedin_client_id or None,
        "scopes": DEFAULT_SCOPES,
        "redirect_path": settings.linkedin_oauth_redirect_path,
        "api_version": settings.linkedin_api_version,
        "blocked_reason": None
        if available
        else (
            "BLOCKED_BY_EXTERNAL_CONFIGURATION: create a LinkedIn Developer app, "
            "enable Sign In with LinkedIn using OpenID Connect + Share on LinkedIn, "
            "then set LINKEDIN_CLIENT_ID + LINKEDIN_CLIENT_SECRET."
        ),
    }


def _state_secret() -> bytes:
    return get_settings().secret_key.encode()


def create_oauth_state(*, agency_id: str, client_id: str, user_id: str) -> str:
    payload = {
        "agency_id": agency_id,
        "client_id": client_id,
        "user_id": user_id,
        "purpose": "linkedin_personal_publish",
        "nonce": secrets.token_urlsafe(16),
        "exp": int(time.time()) + STATE_TTL_SECONDS,
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    signature = hmac.new(_state_secret(), body.encode(), hashlib.sha256).hexdigest()
    return encrypt_secret(f"{body}|{signature}")


def parse_oauth_state(state_token: str) -> dict:
    try:
        raw = decrypt_secret(state_token)
        body, signature = raw.rsplit("|", 1)
        payload = json.loads(body)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid LinkedIn OAuth state") from exc
    expected = hmac.new(_state_secret(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Invalid LinkedIn OAuth state signature")
    if int(payload.get("exp") or 0) < int(time.time()):
        raise HTTPException(status_code=400, detail="LinkedIn OAuth state expired")
    if payload.get("purpose") != "linkedin_personal_publish":
        raise HTTPException(status_code=400, detail="Invalid LinkedIn OAuth purpose")
    return payload


def redirect_uri() -> str:
    settings = get_settings()
    return f"{settings.frontend_url.rstrip('/')}{settings.linkedin_oauth_redirect_path}"


def build_oauth_dialog_url(state: str) -> str | None:
    settings = get_settings()
    if mock_enabled():
        return None
    if not settings.linkedin_client_id:
        return None
    query = urlencode(
        {
            "response_type": "code",
            "client_id": settings.linkedin_client_id,
            "redirect_uri": redirect_uri(),
            "state": state,
            "scope": " ".join(DEFAULT_SCOPES),
        }
    )
    return f"https://www.linkedin.com/oauth/v2/authorization?{query}"


async def exchange_code_for_token(code: str) -> dict:
    if mock_enabled():
        return {
            "access_token": f"mock_linkedin_{secrets.token_hex(8)}",
            "expires_in": 60 * 60 * 24 * 60,
            "scope": " ".join(DEFAULT_SCOPES),
        }
    settings = get_settings()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.linkedin_client_id,
                "client_secret": settings.linkedin_client_secret,
                "redirect_uri": redirect_uri(),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    try:
        payload = response.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid LinkedIn token response") from exc
    if response.status_code >= 400 or not payload.get("access_token"):
        raise HTTPException(
            status_code=400,
            detail=payload.get("error_description") or payload.get("error") or "LinkedIn token exchange failed",
        )
    return payload


async def fetch_member(access_token: str) -> dict:
    if mock_enabled():
        return {
            "sub": "mock-member-123",
            "name": "Mock LinkedIn Member",
            "picture": None,
        }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    try:
        payload = response.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid LinkedIn profile response") from exc
    if response.status_code >= 400 or not payload.get("sub"):
        raise HTTPException(
            status_code=400,
            detail=payload.get("message") or payload.get("error_description") or "Could not read LinkedIn member",
        )
    return payload
