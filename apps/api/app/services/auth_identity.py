"""Google ID token verification and password-reset helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import OAuthAccount, PasswordResetToken, PortalUser, User, now_utc
from ..security import hash_reset_token, new_reset_token


class GoogleIdentity:
    def __init__(self, subject: str, email: str, name: str):
        self.subject = subject
        self.email = email.lower()
        self.name = name or email.split("@")[0]


def verify_google_id_token(id_token: str) -> GoogleIdentity:
    settings = get_settings()
    if not settings.google_oauth_client_id.strip():
        raise HTTPException(status_code=400, detail="Google sign-in is not configured")
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get("https://oauth2.googleapis.com/tokeninfo", params={"id_token": id_token})
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not verify Google token") from exc
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    data = resp.json()
    aud = data.get("aud")
    if aud != settings.google_oauth_client_id:
        raise HTTPException(status_code=401, detail="Google token audience mismatch")
    if data.get("email_verified") not in (True, "true"):
        raise HTTPException(status_code=401, detail="Google email is not verified")
    email = (data.get("email") or "").lower()
    if not email:
        raise HTTPException(status_code=401, detail="Google token missing email")
    return GoogleIdentity(
        subject=str(data.get("sub") or ""),
        email=email,
        name=str(data.get("name") or email.split("@")[0]),
    )


def link_or_get_oauth(
    db: Session,
    *,
    identity: GoogleIdentity,
    user: User | None = None,
    portal_user: PortalUser | None = None,
) -> OAuthAccount:
    existing = db.scalar(
        select(OAuthAccount).where(OAuthAccount.provider == "google", OAuthAccount.subject == identity.subject)
    )
    if existing:
        return existing
    account = OAuthAccount(
        provider="google",
        subject=identity.subject,
        email=identity.email,
        user_id=user.id if user else None,
        portal_user_id=portal_user.id if portal_user else None,
    )
    db.add(account)
    return account


def issue_password_token(
    db: Session,
    *,
    email: str,
    audience: str,
    purpose: str,
    user: User | None = None,
    portal_user: PortalUser | None = None,
    hours: int = 2,
) -> str:
    raw = new_reset_token()
    row = PasswordResetToken(
        email=email.lower(),
        token_hash=hash_reset_token(raw),
        audience=audience,
        purpose=purpose,
        user_id=user.id if user else None,
        portal_user_id=portal_user.id if portal_user else None,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=hours),
    )
    db.add(row)
    return raw


def consume_password_token(db: Session, raw_token: str, purpose: str | None = None) -> PasswordResetToken:
    token_hash = hash_reset_token(raw_token)
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    if not row or row.used_at is not None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    if row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    if purpose and row.purpose != purpose:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    row.used_at = now_utc()
    return row


def generic_forgot_message() -> str:
    return "If an account exists for that email, you will receive reset instructions."
