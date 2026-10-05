from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import LegalAcceptance, User, now_utc
from ..schemas_legal import ChannelConnectConsentIn, LegalDocumentsOut


PLATFORM_TERMS = "platform_terms"
PLATFORM_PRIVACY = "platform_privacy"
CHANNEL_CONNECT = "channel_connect"
CONTENT_PUBLISH = "content_publish"


def legal_documents() -> LegalDocumentsOut:
    settings = get_settings()
    return LegalDocumentsOut(
        tos_version=settings.legal_tos_version,
        privacy_version=settings.legal_privacy_version,
        tos_url=settings.legal_tos_url,
        privacy_url=settings.legal_privacy_url,
    )


def _latest_acceptance(
    db: Session,
    *,
    user_id: uuid.UUID,
    acceptance_type: str,
    document_key: str,
    document_version: str,
) -> LegalAcceptance | None:
    return db.scalar(
        select(LegalAcceptance)
        .where(
            LegalAcceptance.user_id == user_id,
            LegalAcceptance.acceptance_type == acceptance_type,
            LegalAcceptance.document_key == document_key,
            LegalAcceptance.document_version == document_version,
        )
        .order_by(LegalAcceptance.created_at.desc())
        .limit(1)
    )


def platform_status(db: Session, user: User) -> dict:
    docs = legal_documents()
    terms = _latest_acceptance(
        db,
        user_id=user.id,
        acceptance_type=PLATFORM_TERMS,
        document_key="fast_livery_tos",
        document_version=docs.tos_version,
    )
    privacy = _latest_acceptance(
        db,
        user_id=user.id,
        acceptance_type=PLATFORM_PRIVACY,
        document_key="fast_livery_privacy",
        document_version=docs.privacy_version,
    )
    terms_ok = terms is not None
    privacy_ok = privacy is not None
    return {
        "documents": docs,
        "terms_accepted": terms_ok,
        "privacy_accepted": privacy_ok,
        "platform_ready": terms_ok and privacy_ok,
    }


def record_platform_acceptance(
    db: Session,
    *,
    user: User,
    accept_terms: bool,
    accept_privacy: bool,
) -> dict:
    if not accept_terms or not accept_privacy:
        raise HTTPException(status_code=400, detail="Terms and privacy must both be accepted")
    docs = legal_documents()
    now = now_utc()
    if not _latest_acceptance(
        db,
        user_id=user.id,
        acceptance_type=PLATFORM_TERMS,
        document_key="fast_livery_tos",
        document_version=docs.tos_version,
    ):
        db.add(
            LegalAcceptance(
                agency_id=user.agency_id,
                user_id=user.id,
                acceptance_type=PLATFORM_TERMS,
                document_key="fast_livery_tos",
                document_version=docs.tos_version,
                channel=None,
                client_id=None,
                metadata_json={"source": "platform_accept"},
                created_at=now,
            )
        )
    if not _latest_acceptance(
        db,
        user_id=user.id,
        acceptance_type=PLATFORM_PRIVACY,
        document_key="fast_livery_privacy",
        document_version=docs.privacy_version,
    ):
        db.add(
            LegalAcceptance(
                agency_id=user.agency_id,
                user_id=user.id,
                acceptance_type=PLATFORM_PRIVACY,
                document_key="fast_livery_privacy",
                document_version=docs.privacy_version,
                channel=None,
                client_id=None,
                metadata_json={"source": "platform_accept"},
                created_at=now,
            )
        )
    db.commit()
    return platform_status(db, user)


def record_register_acceptance(db: Session, *, user: User) -> None:
    docs = legal_documents()
    now = now_utc()
    db.add(
        LegalAcceptance(
            agency_id=user.agency_id,
            user_id=user.id,
            acceptance_type=PLATFORM_TERMS,
            document_key="fast_livery_tos",
            document_version=docs.tos_version,
            metadata_json={"source": "register"},
            created_at=now,
        )
    )
    db.add(
        LegalAcceptance(
            agency_id=user.agency_id,
            user_id=user.id,
            acceptance_type=PLATFORM_PRIVACY,
            document_key="fast_livery_privacy",
            document_version=docs.privacy_version,
            metadata_json={"source": "register"},
            created_at=now,
        )
    )


def require_platform_ready(db: Session, user: User) -> None:
    status = platform_status(db, user)
    if not status["platform_ready"]:
        raise HTTPException(
            status_code=403,
            detail="Accept Fast Livery terms and privacy policy before connecting channels",
        )


def record_channel_connect_consent(
    db: Session,
    *,
    user: User,
    payload: ChannelConnectConsentIn,
) -> None:
    require_platform_ready(db, user)
    if not payload.admin_confirmed:
        raise HTTPException(status_code=400, detail="Admin authorization confirmation is required")
    if not payload.no_password_stored:
        raise HTTPException(status_code=400, detail="Password storage acknowledgment is required")
    if payload.channel == "instagram" and not payload.ai_disclosure_acknowledged:
        raise HTTPException(status_code=400, detail="AI disclosure acknowledgment is required for Instagram")
    docs = legal_documents()
    db.add(
        LegalAcceptance(
            agency_id=user.agency_id,
            user_id=user.id,
            client_id=payload.client_id,
            acceptance_type=CHANNEL_CONNECT,
            document_key=f"{payload.channel}_connect",
            document_version=docs.tos_version,
            channel=payload.channel,
            metadata_json={
                "admin_confirmed": payload.admin_confirmed,
                "no_password_stored": payload.no_password_stored,
                "ai_disclosure_acknowledged": payload.ai_disclosure_acknowledged,
            },
            created_at=now_utc(),
        )
    )
    db.commit()


def require_fresh_channel_consent(
    db: Session,
    *,
    user: User,
    client_id: uuid.UUID,
    channel: str,
    max_age_minutes: int = 30,
) -> None:
    require_platform_ready(db, user)
    cutoff = now_utc() - timedelta(minutes=max_age_minutes)
    row = db.scalar(
        select(LegalAcceptance)
        .where(
            LegalAcceptance.user_id == user.id,
            LegalAcceptance.client_id == client_id,
            LegalAcceptance.channel == channel,
            LegalAcceptance.acceptance_type == CHANNEL_CONNECT,
            LegalAcceptance.created_at >= cutoff,
        )
        .order_by(LegalAcceptance.created_at.desc())
        .limit(1)
    )
    if row is None:
        raise HTTPException(
            status_code=403,
            detail="Complete the channel connection consent step before OAuth",
        )


def require_publish_approval(
    *,
    human_approved: bool,
    reviewed_exact_content: bool,
) -> None:
    if not human_approved or not reviewed_exact_content:
        raise HTTPException(
            status_code=400,
            detail="Human approval is required before publishing",
        )


def record_publish_approval(
    db: Session,
    *,
    user: User,
    client_id: uuid.UUID,
    channel: str,
    content_id: uuid.UUID,
    metadata: dict | None = None,
) -> None:
    docs = legal_documents()
    db.add(
        LegalAcceptance(
            agency_id=user.agency_id,
            user_id=user.id,
            client_id=client_id,
            acceptance_type=CONTENT_PUBLISH,
            document_key=f"{channel}_publish",
            document_version=docs.tos_version,
            channel=channel,
            metadata_json={"content_id": str(content_id), **(metadata or {})},
            created_at=now_utc(),
        )
    )
