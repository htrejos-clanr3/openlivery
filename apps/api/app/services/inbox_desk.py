"""Shared rules for the operator inbox (labels, canned shortcodes)."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CannedReply, User, now_utc

CONVERSATION_LABELS = ("urgent", "waiting", "follow_up")
MAX_CANNED = 40

DEFAULT_CANNED = (
    ("horario", "Horario", "Estamos abiertos lun–dom 12:00–22:00. ¿Te ayudo con una reserva?"),
    ("momento", "Un momento", "Dame un momento, lo reviso y te confirmo."),
    ("gracias", "Gracias", "Con gusto. Si necesitas algo más, aquí estamos."),
)


def sanitize_labels(values: list[str] | None) -> list[str]:
    allowed = set(CONVERSATION_LABELS)
    seen: list[str] = []
    for item in values or []:
        key = str(item).strip().lower()
        if key in allowed and key not in seen:
            seen.append(key)
    return seen


def shortcode_from(title: str, fallback: str = "atajo") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.strip().lower().lstrip("/"))
    slug = slug.strip("-")[:40]
    return slug or fallback


def normalize_shortcode(value: str | None, title: str) -> str:
    return shortcode_from((value or "").strip() or title)


def allocate_shortcode(db: Session, agency_id: uuid.UUID, desired: str, exclude_id: uuid.UUID | None = None) -> str:
    base = desired[:40]
    for index in range(1, 50):
        candidate = base if index == 1 else f"{base[:36]}-{index}"[:40]
        query = select(CannedReply.id).where(CannedReply.agency_id == agency_id, CannedReply.shortcode == candidate)
        if exclude_id:
            query = query.where(CannedReply.id != exclude_id)
        if not db.scalar(query):
            return candidate
    return f"{base[:32]}-{uuid.uuid4().hex[:6]}"


def seed_default_canned(db: Session, agency_id: uuid.UUID) -> None:
    existing = db.scalar(select(CannedReply.id).where(CannedReply.agency_id == agency_id).limit(1))
    if existing:
        return
    now = now_utc()
    for shortcode, title, body in DEFAULT_CANNED:
        db.add(
            CannedReply(
                agency_id=agency_id,
                shortcode=shortcode,
                title=title,
                body=body,
                created_at=now,
                updated_at=now,
            )
        )


def agency_member(db: Session, agency_id: uuid.UUID, user_id: uuid.UUID | None) -> User | None:
    if not user_id:
        return None
    return db.scalar(select(User).where(User.id == user_id, User.agency_id == agency_id))
