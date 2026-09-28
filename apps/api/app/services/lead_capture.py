"""Automatic lead capture for one client tenant.

Channel events call ``safe_capture``. Failures are stored on ``lead_capture_events``
and never break the inbound chat pipeline. This is not a Zapier-style engine.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..models import (
    Contact,
    Conversation,
    Lead,
    LeadActivity,
    LeadCaptureEvent,
    LeadCaptureSettings,
    LeadNotification,
    LeadPipeline,
    LeadStage,
    User,
    new_public_id,
    now_utc,
)
from .lead_detection import detection_service

logger = logging.getLogger(__name__)

SOURCES = ("whatsapp", "instagram", "facebook", "form", "webhook", "widget")
DEFAULT_SOURCES = ["whatsapp", "form", "webhook"]
CHANNEL_TO_SOURCE = {
    "whatsapp": "whatsapp",
    "whatsapp_cloud": "whatsapp",
    "widget": "widget",
}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DEFAULT_STAGES = (
    ("Nuevo", "new", 0),
    ("Contactado", "contacted", 1),
    ("Calificado", "qualified", 2),
    ("Propuesta", "proposal", 3),
    ("Ganado", "won", 4),
    ("Perdido", "lost", 5),
)
CLOSED_STAGE_SLUGS = frozenset({"won", "lost"})
DEFAULT_TRIGGERS = ["new_contact", "form", "webhook"]
STALE_AFTER = timedelta(days=7)


def normalize_name(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())[:180]


def normalize_company(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())[:180]


def normalize_email(value: str | None) -> str | None:
    text = (value or "").strip().lower()
    if not text or not EMAIL_RE.match(text):
        return None
    return text[:320]


def normalize_phone(value: str | None) -> str | None:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) < 7:
        return None
    return digits[:32]


def phone_from_chat_id(external_chat_id: str | None) -> str | None:
    if not external_chat_id:
        return None
    return normalize_phone(external_chat_id.split("@")[0].split(":")[-1])


def source_from_channel(channel: str | None) -> str:
    return CHANNEL_TO_SOURCE.get((channel or "").strip(), (channel or "").strip() or "webhook")


def trigger_from_source(source: str) -> str:
    if source in {"form", "webhook"}:
        return source
    return "new_contact"


def _json_object(value: dict) -> dict:
    dumped = json.loads(json.dumps(value, default=str))
    return dumped if isinstance(dumped, dict) else {"value": dumped}


def _automation_config(settings: LeadCaptureSettings) -> dict:
    raw = settings.automation_config if isinstance(settings.automation_config, dict) else {}
    triggers = raw.get("triggers")
    if not isinstance(triggers, list) or not triggers:
        triggers = list(DEFAULT_TRIGGERS)
    return {
        "triggers": [str(item) for item in triggers],
        "require_commercial_intent": bool(raw.get("require_commercial_intent")),
    }


def ensure_settings(db: Session, *, agency_id: uuid.UUID, client_id: uuid.UUID) -> LeadCaptureSettings:
    settings = db.scalar(
        select(LeadCaptureSettings)
        .options(
            selectinload(LeadCaptureSettings.default_pipeline).selectinload(LeadPipeline.stages),
            selectinload(LeadCaptureSettings.default_stage),
            selectinload(LeadCaptureSettings.default_assignee),
        )
        .where(LeadCaptureSettings.client_id == client_id, LeadCaptureSettings.agency_id == agency_id)
    )
    if settings:
        if not settings.default_pipeline_id:
            pipeline = _default_pipeline(db, agency_id=agency_id, client_id=client_id)
            settings.default_pipeline_id = pipeline.id
            settings.default_stage_id = pipeline.stages[0].id if pipeline.stages else None
            db.flush()
        elif settings.default_pipeline:
            _ensure_stages(db, settings.default_pipeline)
        return settings

    pipeline = _default_pipeline(db, agency_id=agency_id, client_id=client_id)
    settings = LeadCaptureSettings(
        agency_id=agency_id,
        client_id=client_id,
        enabled=False,
        sources=list(DEFAULT_SOURCES),
        default_pipeline_id=pipeline.id,
        default_stage_id=pipeline.stages[0].id if pipeline.stages else None,
        auto_tags=[],
        notify_on_new_lead=True,
        ingest_token=new_public_id(),
        automation_config={"triggers": list(DEFAULT_TRIGGERS), "require_commercial_intent": False},
    )
    db.add(settings)
    db.flush()
    return settings


def _default_pipeline(db: Session, *, agency_id: uuid.UUID, client_id: uuid.UUID) -> LeadPipeline:
    pipeline = db.scalar(
        select(LeadPipeline)
        .options(selectinload(LeadPipeline.stages))
        .where(
            LeadPipeline.client_id == client_id,
            LeadPipeline.agency_id == agency_id,
            LeadPipeline.is_default.is_(True),
        )
    )
    if pipeline:
        _ensure_stages(db, pipeline)
        return pipeline
    pipeline = LeadPipeline(agency_id=agency_id, client_id=client_id, name="Principal", is_default=True)
    db.add(pipeline)
    db.flush()
    _seed_stages(db, pipeline)
    db.flush()
    db.refresh(pipeline)
    return pipeline


def _ensure_stages(db: Session, pipeline: LeadPipeline) -> None:
    have = {stage.slug for stage in (pipeline.stages or [])}
    added = False
    for name, slug, position in DEFAULT_STAGES:
        if slug in have:
            continue
        db.add(
            LeadStage(
                agency_id=pipeline.agency_id,
                client_id=pipeline.client_id,
                pipeline_id=pipeline.id,
                name=name,
                slug=slug,
                position=position,
            )
        )
        added = True
    if added:
        db.flush()
        db.refresh(pipeline)


def _seed_stages(db: Session, pipeline: LeadPipeline) -> None:
    for name, slug, position in DEFAULT_STAGES:
        db.add(
            LeadStage(
                agency_id=pipeline.agency_id,
                client_id=pipeline.client_id,
                pipeline_id=pipeline.id,
                name=name,
                slug=slug,
                position=position,
            )
        )


def rotate_ingest_token(db: Session, settings: LeadCaptureSettings) -> LeadCaptureSettings:
    settings.ingest_token = new_public_id()
    settings.updated_at = now_utc()
    db.flush()
    return settings


def find_contact(
    db: Session,
    *,
    agency_id: uuid.UUID,
    client_id: uuid.UUID,
    channel_identifier: str | None,
    email: str | None,
    phone: str | None,
) -> Contact | None:
    scope = (Contact.agency_id == agency_id, Contact.client_id == client_id)
    if channel_identifier:
        found = db.scalar(select(Contact).where(*scope, Contact.channel_identifier == channel_identifier))
        if found:
            return found
    if email:
        found = db.scalar(select(Contact).where(*scope, Contact.email == email))
        if found:
            return found
    if phone:
        found = db.scalar(select(Contact).where(*scope, Contact.phone == phone))
        if found:
            return found
    return None


def find_open_lead(
    db: Session,
    *,
    agency_id: uuid.UUID,
    client_id: uuid.UUID,
    contact_id: uuid.UUID,
) -> Lead | None:
    rows = db.scalars(
        select(Lead)
        .options(selectinload(Lead.stage))
        .where(Lead.agency_id == agency_id, Lead.client_id == client_id, Lead.contact_id == contact_id)
        .order_by(Lead.last_activity_at.desc(), Lead.created_at.desc())
    ).all()
    for lead in rows:
        slug = lead.stage.slug if lead.stage else "new"
        if slug not in CLOSED_STAGE_SLUGS:
            return lead
    return None


def _add_activity(
    db: Session,
    lead: Lead,
    *,
    kind: str,
    message: str,
    user_id: uuid.UUID | None = None,
) -> None:
    db.add(
        LeadActivity(
            agency_id=lead.agency_id,
            client_id=lead.client_id,
            lead_id=lead.id,
            user_id=user_id,
            kind=kind,
            message=message[:2000],
        )
    )
    lead.last_activity_at = now_utc()
    lead.updated_at = now_utc()


def _notify(db: Session, lead: Lead, settings: LeadCaptureSettings) -> None:
    if not settings.notify_on_new_lead:
        return
    recipients: list[uuid.UUID]
    if lead.assigned_user_id:
        recipients = [lead.assigned_user_id]
    else:
        recipients = list(db.scalars(select(User.id).where(User.agency_id == lead.agency_id)).all())
    for user_id in recipients:
        db.add(
            LeadNotification(
                agency_id=lead.agency_id,
                client_id=lead.client_id,
                user_id=user_id,
                lead_id=lead.id,
                kind="new_lead",
            )
        )


def _write_event(
    db: Session,
    *,
    agency_id: uuid.UUID,
    client_id: uuid.UUID,
    source: str,
    payload: dict,
    status: str,
    error_message: str | None = None,
    lead_id: uuid.UUID | None = None,
    contact_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
    existing: LeadCaptureEvent | None = None,
) -> LeadCaptureEvent:
    if existing:
        existing.status = status
        existing.error_message = error_message
        existing.lead_id = lead_id
        existing.contact_id = contact_id
        existing.conversation_id = conversation_id
        existing.attempt_count = (existing.attempt_count or 1) + 1
        existing.updated_at = now_utc()
        return existing
    row = LeadCaptureEvent(
        agency_id=agency_id,
        client_id=client_id,
        source=source,
        payload=_json_object(payload),
        status=status,
        error_message=error_message,
        lead_id=lead_id,
        contact_id=contact_id,
        conversation_id=conversation_id,
        attempt_count=1,
    )
    db.add(row)
    return row


def _upsert_contact(
    db: Session,
    *,
    agency_id: uuid.UUID,
    client_id: uuid.UUID,
    source: str,
    name: str | None,
    email: str | None,
    phone: str | None,
    channel_identifier: str | None,
    company: str | None,
    extra: dict,
) -> tuple[Contact, bool]:
    clean_name = normalize_name(name)
    clean_email = normalize_email(email)
    clean_phone = normalize_phone(phone)
    ident = (channel_identifier or "").strip()[:255] or None
    clean_company = normalize_company(company)
    contact = find_contact(
        db,
        agency_id=agency_id,
        client_id=client_id,
        channel_identifier=ident,
        email=clean_email,
        phone=clean_phone,
    )
    created = contact is None
    if contact is None:
        contact = Contact(
            agency_id=agency_id,
            client_id=client_id,
            name=clean_name,
            company=clean_company,
            email=clean_email,
            phone=clean_phone,
            channel_identifier=ident,
            source=source,
            extra=_json_object(extra or {}),
        )
        db.add(contact)
        db.flush()
        return contact, True
    if clean_name and (not contact.name or contact.name == contact.channel_identifier):
        contact.name = clean_name
    elif clean_name and len(clean_name) > len(contact.name or ""):
        contact.name = clean_name
    if clean_company and not contact.company:
        contact.company = clean_company
    if clean_email and not contact.email:
        contact.email = clean_email
    if clean_phone and not contact.phone:
        contact.phone = clean_phone
    if ident and not contact.channel_identifier:
        contact.channel_identifier = ident
    contact.updated_at = now_utc()
    return contact, created


def _bind_conversation(
    db: Session,
    *,
    agency_id: uuid.UUID,
    client_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
    contact: Contact,
    name: str | None,
) -> None:
    if not conversation_id:
        return
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.agency_id == agency_id,
            Conversation.client_id == client_id,
        )
    )
    if not conversation:
        return
    conversation.contact_id = contact.id
    if name:
        conversation.contact_name = normalize_name(name)


def capture(
    db: Session,
    *,
    agency_id: uuid.UUID,
    client_id: uuid.UUID,
    source: str,
    name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    channel_identifier: str | None = None,
    conversation_id: uuid.UUID | None = None,
    extra: dict | None = None,
    payload: dict | None = None,
    event: LeadCaptureEvent | None = None,
    trigger: str | None = None,
    company: str | None = None,
    text: str | None = None,
    mark_ingest: bool = False,
) -> LeadCaptureEvent:
    source = (source or "").strip()
    if source not in SOURCES:
        raise ValueError(f"Unknown lead source: {source}")
    extra = extra or {}
    company = company or extra.get("company") or (payload or {}).get("company")
    text = text or extra.get("text") or extra.get("preview")
    trigger = trigger or trigger_from_source(source)
    raw = _json_object(
        {
            "source": source,
            "name": name,
            "email": email,
            "phone": phone,
            "channel_identifier": channel_identifier,
            "company": company,
            "trigger": trigger,
            "extra": extra,
            **(payload or {}),
        }
    )
    raw.update(
        {
            "source": source,
            "name": name,
            "email": email,
            "phone": phone,
            "channel_identifier": channel_identifier,
            "trigger": trigger,
        }
    )
    settings = ensure_settings(db, agency_id=agency_id, client_id=client_id)
    if not settings.enabled:
        return _write_event(
            db,
            agency_id=agency_id,
            client_id=client_id,
            source=source,
            payload=raw,
            status="skipped",
            error_message="Lead capture is disabled for this client.",
            conversation_id=conversation_id,
            existing=event,
        )
    enabled_sources = {str(item) for item in (settings.sources or [])}
    if source not in enabled_sources:
        return _write_event(
            db,
            agency_id=agency_id,
            client_id=client_id,
            source=source,
            payload=raw,
            status="skipped",
            error_message=f"Source {source} is not enabled.",
            conversation_id=conversation_id,
            existing=event,
        )

    contact, created_contact = _upsert_contact(
        db,
        agency_id=agency_id,
        client_id=client_id,
        source=source,
        name=name,
        email=email,
        phone=phone,
        channel_identifier=channel_identifier,
        company=company,
        extra=extra,
    )
    _bind_conversation(
        db,
        agency_id=agency_id,
        client_id=client_id,
        conversation_id=conversation_id,
        contact=contact,
        name=name,
    )

    config = _automation_config(settings)
    allowed_triggers = set(config["triggers"])
    if trigger not in allowed_triggers:
        return _write_event(
            db,
            agency_id=agency_id,
            client_id=client_id,
            source=source,
            payload=raw,
            status="skipped",
            error_message=f"Trigger {trigger} is not enabled.",
            contact_id=contact.id,
            conversation_id=conversation_id,
            existing=event,
        )

    detected = detection_service.detect(source=source, enabled_sources=enabled_sources, text=text)
    if config["require_commercial_intent"] and not detected.should_create_lead:
        return _write_event(
            db,
            agency_id=agency_id,
            client_id=client_id,
            source=source,
            payload=raw,
            status="skipped",
            error_message=f"No commercial intent ({detected.reason}).",
            contact_id=contact.id,
            conversation_id=conversation_id,
            existing=event,
        )
    if not detected.should_create_lead:
        return _write_event(
            db,
            agency_id=agency_id,
            client_id=client_id,
            source=source,
            payload=raw,
            status="skipped",
            error_message=f"Lead not created ({detected.reason}).",
            contact_id=contact.id,
            conversation_id=conversation_id,
            existing=event,
        )

    lead = find_open_lead(db, agency_id=agency_id, client_id=client_id, contact_id=contact.id)
    created_lead = lead is None
    tags = [str(tag).strip() for tag in (settings.auto_tags or []) if str(tag).strip()]
    if lead is None:
        lead = Lead(
            agency_id=agency_id,
            client_id=client_id,
            contact_id=contact.id,
            conversation_id=conversation_id,
            pipeline_id=settings.default_pipeline_id,
            stage_id=settings.default_stage_id,
            assigned_user_id=settings.default_assignee_user_id,
            source=source,
            tags=tags,
            last_activity_at=now_utc(),
        )
        db.add(lead)
        db.flush()
        _add_activity(db, lead, kind="created", message=f"Lead created from {source}.")
        try:
            _notify(db, lead, settings)
        except Exception as exc:
            logger.exception("Lead notification failed for client %s", client_id)
            return _write_event(
                db,
                agency_id=agency_id,
                client_id=client_id,
                source=source,
                payload=raw,
                status="error",
                error_message=f"Lead created but notification failed: {exc}",
                lead_id=lead.id,
                contact_id=contact.id,
                conversation_id=conversation_id,
                existing=event,
            )
    else:
        if conversation_id:
            lead.conversation_id = conversation_id
        if source and source != lead.source:
            lead.source = source
        if tags:
            lead.tags = list(dict.fromkeys([*(lead.tags or []), *tags]))
        if settings.default_assignee_user_id and not lead.assigned_user_id:
            lead.assigned_user_id = settings.default_assignee_user_id
        _add_activity(db, lead, kind="capture", message=f"Inbound activity from {source}.")

    if mark_ingest:
        settings.last_ingest_at = now_utc()

    status = "success"
    note = None
    if not created_lead:
        note = "Updated existing open lead."
    elif not created_contact:
        note = "Created lead for existing contact."
    return _write_event(
        db,
        agency_id=agency_id,
        client_id=client_id,
        source=source,
        payload=raw,
        status=status,
        error_message=note,
        lead_id=lead.id,
        contact_id=contact.id,
        conversation_id=conversation_id,
        existing=event,
    )


def touch_open_lead(
    db: Session,
    *,
    agency_id: uuid.UUID,
    client_id: uuid.UUID,
    source: str,
    name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    channel_identifier: str | None = None,
    conversation_id: uuid.UUID | None = None,
) -> Lead | None:
    """Update last activity on an open lead. Never creates a lead."""
    contact = find_contact(
        db,
        agency_id=agency_id,
        client_id=client_id,
        channel_identifier=(channel_identifier or "").strip()[:255] or None,
        email=normalize_email(email),
        phone=normalize_phone(phone),
    )
    if not contact:
        return None
    _bind_conversation(
        db,
        agency_id=agency_id,
        client_id=client_id,
        conversation_id=conversation_id,
        contact=contact,
        name=name,
    )
    lead = find_open_lead(db, agency_id=agency_id, client_id=client_id, contact_id=contact.id)
    if not lead:
        return None
    if conversation_id:
        lead.conversation_id = conversation_id
    _add_activity(db, lead, kind="message", message=f"New message on {source}.")
    return lead


def safe_capture(db: Session, **kwargs: Any) -> LeadCaptureEvent | None:
    """Run capture without raising. Used from WhatsApp / widget inbound paths."""
    try:
        row = capture(db, **kwargs)
        db.commit()
        return row
    except Exception as exc:
        logger.exception("Lead capture failed")
        db.rollback()
        try:
            row = _write_event(
                db,
                agency_id=kwargs["agency_id"],
                client_id=kwargs["client_id"],
                source=str(kwargs.get("source") or ""),
                payload=_json_object(kwargs.get("payload") or kwargs.get("extra") or {}),
                status="error",
                error_message=str(exc),
                conversation_id=kwargs.get("conversation_id"),
            )
            db.commit()
            return row
        except Exception:
            db.rollback()
            logger.exception("Could not persist lead capture error")
            return None


def safe_touch_open_lead(db: Session, **kwargs: Any) -> Lead | None:
    try:
        lead = touch_open_lead(db, **kwargs)
        db.commit()
        return lead
    except Exception:
        logger.exception("Lead activity touch failed")
        db.rollback()
        return None


def retry_event(db: Session, event: LeadCaptureEvent) -> LeadCaptureEvent:
    payload = event.payload or {}
    return capture(
        db,
        agency_id=event.agency_id,
        client_id=event.client_id,
        source=event.source or str(payload.get("source") or "webhook"),
        name=payload.get("name"),
        email=payload.get("email"),
        phone=payload.get("phone"),
        channel_identifier=payload.get("channel_identifier"),
        conversation_id=event.conversation_id,
        extra=payload.get("extra") if isinstance(payload.get("extra"), dict) else payload,
        payload=payload,
        event=event,
        trigger=payload.get("trigger"),
        company=payload.get("company"),
    )


def create_manual_lead(
    db: Session,
    *,
    agency_id: uuid.UUID,
    client_id: uuid.UUID,
    name: str,
    email: str | None = None,
    phone: str | None = None,
    company: str | None = None,
    source: str = "form",
    channel_identifier: str | None = None,
    stage_id: uuid.UUID | None = None,
    assigned_user_id: uuid.UUID | None = None,
    tags: list[str] | None = None,
    notes: str | None = None,
    next_action: str | None = None,
    user_id: uuid.UUID | None = None,
) -> Lead:
    settings = ensure_settings(db, agency_id=agency_id, client_id=client_id)
    source = source if source in SOURCES else "form"
    contact, _ = _upsert_contact(
        db,
        agency_id=agency_id,
        client_id=client_id,
        source=source,
        name=name,
        email=email,
        phone=phone,
        channel_identifier=channel_identifier,
        company=company,
        extra={},
    )
    lead = Lead(
        agency_id=agency_id,
        client_id=client_id,
        contact_id=contact.id,
        pipeline_id=settings.default_pipeline_id,
        stage_id=stage_id or settings.default_stage_id,
        assigned_user_id=assigned_user_id if assigned_user_id is not None else settings.default_assignee_user_id,
        source=source,
        tags=[str(tag).strip() for tag in (tags or []) if str(tag).strip()],
        notes=(notes or "").strip(),
        next_action=(next_action or "").strip()[:240],
        last_activity_at=now_utc(),
    )
    db.add(lead)
    db.flush()
    _add_activity(db, lead, kind="created", message="Lead created manually.", user_id=user_id)
    try:
        _notify(db, lead, settings)
    except Exception:
        logger.exception("Lead notification failed for manual create")
    return lead


def lead_stats(db: Session, *, agency_id: uuid.UUID, client_id: uuid.UUID) -> dict[str, int]:
    scope = (Lead.agency_id == agency_id, Lead.client_id == client_id)
    stale_before = now_utc() - STALE_AFTER

    def count(*extra):
        return int(db.scalar(select(func.count()).select_from(Lead).where(*scope, *extra)) or 0)

    new_count = int(
        db.scalar(
            select(func.count())
            .select_from(Lead)
            .join(LeadStage, Lead.stage_id == LeadStage.id)
            .where(*scope, LeadStage.slug == "new")
        )
        or 0
    )
    qualified_count = int(
        db.scalar(
            select(func.count())
            .select_from(Lead)
            .join(LeadStage, Lead.stage_id == LeadStage.id)
            .where(*scope, LeadStage.slug == "qualified")
        )
        or 0
    )
    return {
        "new_count": new_count,
        "qualified_count": qualified_count,
        "unassigned_count": count(Lead.assigned_user_id.is_(None)),
        "stale_count": count(or_(Lead.last_activity_at.is_(None), Lead.last_activity_at < stale_before)),
        "total_count": count(),
    }


def ingest_stats(db: Session, *, agency_id: uuid.UUID, client_id: uuid.UUID, settings: LeadCaptureSettings) -> dict:
    last_event = db.scalar(
        select(LeadCaptureEvent)
        .where(LeadCaptureEvent.agency_id == agency_id, LeadCaptureEvent.client_id == client_id)
        .order_by(LeadCaptureEvent.created_at.desc())
        .limit(1)
    )
    created = int(
        db.scalar(
            select(func.count())
            .select_from(LeadCaptureEvent)
            .where(
                LeadCaptureEvent.agency_id == agency_id,
                LeadCaptureEvent.client_id == client_id,
                LeadCaptureEvent.status == "success",
                LeadCaptureEvent.lead_id.is_not(None),
            )
        )
        or 0
    )
    return {
        "last_ingest_at": settings.last_ingest_at or (last_event.created_at if last_event else None),
        "last_ingest_status": last_event.status if last_event else None,
        "leads_created_count": created,
    }
