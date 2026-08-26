"""Signed public URLs so Meta can fetch media without auth cookies."""

from __future__ import annotations

import hashlib
import hmac
import time
import uuid

from fastapi import HTTPException

from ..config import get_settings


def _secret() -> bytes:
    return get_settings().encryption_key.encode()


def sign_media_asset(asset_id: uuid.UUID, *, ttl_seconds: int | None = None) -> tuple[int, str]:
    settings = get_settings()
    ttl = ttl_seconds if ttl_seconds is not None else settings.instagram_media_url_ttl_seconds
    exp = int(time.time()) + max(60, ttl)
    payload = f"{asset_id}:{exp}".encode()
    sig = hmac.new(_secret(), payload, hashlib.sha256).hexdigest()
    return exp, sig


def verify_media_signature(asset_id: uuid.UUID, exp: int, sig: str) -> None:
    if int(exp) < int(time.time()):
        raise HTTPException(status_code=403, detail="Media URL expired")
    payload = f"{asset_id}:{int(exp)}".encode()
    expected = hmac.new(_secret(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig or ""):
        raise HTTPException(status_code=403, detail="Invalid media signature")


def public_media_url(asset_id: uuid.UUID, *, ttl_seconds: int | None = None) -> str:
    settings = get_settings()
    exp, sig = sign_media_asset(asset_id, ttl_seconds=ttl_seconds)
    base = settings.backend_url.rstrip("/")
    return f"{base}/api/public/media-assets/{asset_id}?exp={exp}&sig={sig}"
