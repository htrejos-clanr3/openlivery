"""Per-client lead capture: settings, leads, audit, public form/webhook ingest."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..models import (
    Client,
    Contact,
    Lead,
    LeadActivity,
    LeadCaptureEvent,
    LeadCaptureSettings,
    LeadNotification,
    LeadPipeline,
    LeadStage,
    User,
    now_utc,
)
from ..ratelimit import lead_ingest_rate_limit
from ..schemas_leads import (
    AssigneeOut,
    LeadActivityIn,
    LeadActivityOut,
    LeadCaptureEventOut,
    LeadCaptureSettingsOut,
    LeadCaptureSettingsUpdate,
    LeadCreateIn,
    LeadNotificationOut,
    LeadOut,
    LeadPipelineOut,
    LeadStatsOut,
    LeadUpdateIn,
    PublicLeadIn,
)
from ..services import lead_capture as capture
from ..services.lead_capture import SOURCES


router = APIRouter(prefix="/clients/{client_id}/lead-capture", tags=["Lead capture"])
leads_router = APIRouter(prefix="/clients/{client_id}/leads", tags=["Leads"])
notifications_router = APIRouter(prefix="/leads", tags=["Leads"])
public_router = APIRouter(prefix="/public/lead-capture", tags=["Lead capture"])


def _client(db: Session, user: User, client_id: uuid.UUID) -> Client:
    client = db.scalar(select(Client).where(Client.id == client_id, Client.agency_id == user.agency_id))
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def _load_settings(db: Session, settings_id: uuid.UUID) -> LeadCaptureSettings:
    settings = db.scalar(
        select(LeadCaptureSettings)
        .options(
            selectinload(LeadCaptureSettings.default_pipeline).selectinload(LeadPipeline.stages),
            selectinload(LeadCaptureSettings.default_stage),
            selectinload(LeadCaptureSettings.default_assignee),
        )
        .where(LeadCaptureSettings.id == settings_id)
    )
    if not settings:
        raise HTTPException(status_code=404, detail="Lead capture settings not found")
    return settings


def _settings_out(db: Session, settings: LeadCaptureSettings) -> LeadCaptureSettingsOut:
    assignees = db.scalars(select(User).where(User.agency_id == settings.agency_id).order_by(User.name)).all()
    pipeline = settings.default_pipeline
    stats = capture.ingest_stats(
        db, agency_id=settings.agency_id, client_id=settings.client_id, settings=settings
    )
    return LeadCaptureSettingsOut(
        id=settings.id,
        client_id=settings.client_id,
        enabled=settings.enabled,
        sources=list(settings.sources or []),
        default_pipeline_id=settings.default_pipeline_id,
        default_stage_id=settings.default_stage_id,
        default_assignee_user_id=settings.default_assignee_user_id,
        auto_tags=list(settings.auto_tags or []),
        notify_on_new_lead=settings.notify_on_new_lead,
        ingest_token=settings.ingest_token,
        last_ingest_at=stats["last_ingest_at"],
        last_ingest_status=stats["last_ingest_status"],
        leads_created_count=stats["leads_created_count"],
        automation_config=capture._automation_config(settings),
        pipeline=LeadPipelineOut.model_validate(pipeline) if pipeline else None,
        assignees=[AssigneeOut.model_validate(item) for item in assignees],
    )


def _lead_out(lead: Lead, *, include_activities: bool = False) -> LeadOut:
    activities: list[LeadActivityOut] = []
    if include_activities:
        activities = [LeadActivityOut.model_validate(item) for item in (lead.activities or [])]
    return LeadOut(
        id=lead.id,
        client_id=lead.client_id,
        source=lead.source,
        tags=list(lead.tags or []),
        contact=lead.contact,
        conversation_id=lead.conversation_id,
        pipeline_id=lead.pipeline_id,
        stage_id=lead.stage_id,
        stage_name=lead.stage.name if lead.stage else None,
        stage_slug=lead.stage.slug if lead.stage else None,
        assigned_user_id=lead.assigned_user_id,
        assignee_name=lead.assignee.name if lead.assignee else None,
        notes=lead.notes or "",
        next_action=lead.next_action or "",
        score=lead.score,
        last_activity_at=lead.last_activity_at,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
        activities=activities,
    )


def _scoped_lead(db: Session, client: Client, lead_id: uuid.UUID, *, with_activities: bool = False) -> Lead:
    options = [selectinload(Lead.contact), selectinload(Lead.stage), selectinload(Lead.assignee)]
    if with_activities:
        options.append(selectinload(Lead.activities))
    lead = db.scalar(
        select(Lead)
        .options(*options)
        .where(Lead.id == lead_id, Lead.client_id == client.id, Lead.agency_id == client.agency_id)
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.get("", response_model=LeadCaptureSettingsOut)
def get_settings(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    settings = capture.ensure_settings(db, agency_id=client.agency_id, client_id=client.id)
    db.commit()
    return _settings_out(db, _load_settings(db, settings.id))


@router.put("", response_model=LeadCaptureSettingsOut)
def update_settings(
    client_id: uuid.UUID,
    payload: LeadCaptureSettingsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    settings = capture.ensure_settings(db, agency_id=client.agency_id, client_id=client.id)
    data = payload.model_dump(exclude_unset=True)
    if "sources" in data and data["sources"] is not None:
        unknown = [item for item in data["sources"] if item not in SOURCES]
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unknown sources: {', '.join(unknown)}")
        settings.sources = list(dict.fromkeys(data["sources"]))
        del data["sources"]
    if "auto_tags" in data and data["auto_tags"] is not None:
        settings.auto_tags = [str(tag).strip() for tag in data["auto_tags"] if str(tag).strip()][:20]
        del data["auto_tags"]
    if "default_assignee_user_id" in data:
        assignee_id = data["default_assignee_user_id"]
        if assignee_id:
            assignee = db.scalar(select(User).where(User.id == assignee_id, User.agency_id == client.agency_id))
            if not assignee:
                raise HTTPException(status_code=400, detail="Assignee is not in this agency.")
        settings.default_assignee_user_id = assignee_id
        del data["default_assignee_user_id"]
    if "automation_config" in data and data["automation_config"] is not None:
        raw = data["automation_config"] if isinstance(data["automation_config"], dict) else {}
        triggers = raw.get("triggers") if isinstance(raw.get("triggers"), list) else capture.DEFAULT_TRIGGERS
        settings.automation_config = {
            "triggers": [str(item) for item in triggers],
            "require_commercial_intent": bool(raw.get("require_commercial_intent")),
        }
        del data["automation_config"]
    for key, value in data.items():
        setattr(settings, key, value)
    db.commit()
    refreshed = capture.ensure_settings(db, agency_id=client.agency_id, client_id=client.id)
    return _settings_out(db, _load_settings(db, refreshed.id))


@router.post("/token", response_model=LeadCaptureSettingsOut)
def rotate_token(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    settings = capture.ensure_settings(db, agency_id=client.agency_id, client_id=client.id)
    capture.rotate_ingest_token(db, settings)
    db.commit()
    return _settings_out(db, _load_settings(db, settings.id))


@router.get("/events", response_model=list[LeadCaptureEventOut])
def list_events(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    rows = db.scalars(
        select(LeadCaptureEvent)
        .where(LeadCaptureEvent.client_id == client.id, LeadCaptureEvent.agency_id == client.agency_id)
        .order_by(LeadCaptureEvent.created_at.desc())
        .limit(50)
    ).all()
    return rows


@router.post("/events/{event_id}/retry", response_model=LeadCaptureEventOut)
def retry_event(
    client_id: uuid.UUID,
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    event = db.scalar(
        select(LeadCaptureEvent).where(
            LeadCaptureEvent.id == event_id,
            LeadCaptureEvent.client_id == client.id,
            LeadCaptureEvent.agency_id == client.agency_id,
        )
    )
    if not event:
        raise HTTPException(status_code=404, detail="Capture event not found")
    try:
        row = capture.retry_event(db, event)
        db.commit()
        db.refresh(row)
        return row
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@leads_router.get("/stats", response_model=LeadStatsOut)
def get_lead_stats(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    return LeadStatsOut(**capture.lead_stats(db, agency_id=client.agency_id, client_id=client.id))


@leads_router.get("", response_model=list[LeadOut])
def list_leads(
    client_id: uuid.UUID,
    q: str | None = Query(default=None),
    stage_id: uuid.UUID | None = Query(default=None),
    assigned_user_id: uuid.UUID | None = Query(default=None),
    unassigned: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    stmt = (
        select(Lead)
        .options(selectinload(Lead.contact), selectinload(Lead.stage), selectinload(Lead.assignee))
        .where(Lead.client_id == client.id, Lead.agency_id == client.agency_id)
    )
    if stage_id:
        stmt = stmt.where(Lead.stage_id == stage_id)
    if unassigned:
        stmt = stmt.where(Lead.assigned_user_id.is_(None))
    elif assigned_user_id:
        stmt = stmt.where(Lead.assigned_user_id == assigned_user_id)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.join(Contact).where(
            or_(
                Contact.name.ilike(like),
                Contact.email.ilike(like),
                Contact.phone.ilike(like),
                Contact.company.ilike(like),
            )
        )
    rows = db.scalars(stmt.order_by(Lead.last_activity_at.desc(), Lead.created_at.desc()).limit(200)).all()
    return [_lead_out(row) for row in rows]


@leads_router.post("", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def create_lead(
    client_id: uuid.UUID,
    payload: LeadCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    if payload.assigned_user_id:
        assignee = db.scalar(select(User).where(User.id == payload.assigned_user_id, User.agency_id == client.agency_id))
        if not assignee:
            raise HTTPException(status_code=400, detail="Assignee is not in this agency.")
    if payload.stage_id:
        stage = db.scalar(
            select(LeadStage).where(
                LeadStage.id == payload.stage_id,
                LeadStage.client_id == client.id,
                LeadStage.agency_id == client.agency_id,
            )
        )
        if not stage:
            raise HTTPException(status_code=400, detail="Stage not found for this client.")
    lead = capture.create_manual_lead(
        db,
        agency_id=client.agency_id,
        client_id=client.id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        company=payload.company,
        source=payload.source,
        channel_identifier=payload.channel_identifier,
        stage_id=payload.stage_id,
        assigned_user_id=payload.assigned_user_id,
        tags=payload.tags,
        notes=payload.notes,
        next_action=payload.next_action,
        user_id=user.id,
    )
    db.commit()
    return _lead_out(_scoped_lead(db, client, lead.id, with_activities=True), include_activities=True)


@leads_router.get("/{lead_id}", response_model=LeadOut)
def get_lead(
    client_id: uuid.UUID,
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    return _lead_out(_scoped_lead(db, client, lead_id, with_activities=True), include_activities=True)


@leads_router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(
    client_id: uuid.UUID,
    lead_id: uuid.UUID,
    payload: LeadUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    lead = _scoped_lead(db, client, lead_id, with_activities=True)
    data = payload.model_dump(exclude_unset=True)
    notes = []
    if "stage_id" in data:
        stage_id = data["stage_id"]
        if stage_id:
            stage = db.scalar(
                select(LeadStage).where(
                    LeadStage.id == stage_id,
                    LeadStage.client_id == client.id,
                    LeadStage.agency_id == client.agency_id,
                )
            )
            if not stage:
                raise HTTPException(status_code=400, detail="Stage not found for this client.")
            lead.stage_id = stage.id
            notes.append(f"Stage set to {stage.name}.")
        else:
            lead.stage_id = None
    if "assigned_user_id" in data:
        assignee_id = data["assigned_user_id"]
        if assignee_id:
            assignee = db.scalar(select(User).where(User.id == assignee_id, User.agency_id == client.agency_id))
            if not assignee:
                raise HTTPException(status_code=400, detail="Assignee is not in this agency.")
            lead.assigned_user_id = assignee.id
            notes.append(f"Assigned to {assignee.name}.")
        else:
            lead.assigned_user_id = None
            notes.append("Owner cleared.")
    if "tags" in data and data["tags"] is not None:
        lead.tags = [str(tag).strip() for tag in data["tags"] if str(tag).strip()]
    if "notes" in data and data["notes"] is not None:
        lead.notes = data["notes"]
    if "next_action" in data and data["next_action"] is not None:
        lead.next_action = str(data["next_action"])[:240]
    contact = lead.contact
    if "name" in data and data["name"]:
        contact.name = capture.normalize_name(data["name"])
    if "email" in data:
        contact.email = capture.normalize_email(data["email"])
    if "phone" in data:
        contact.phone = capture.normalize_phone(data["phone"])
    if "company" in data and data["company"] is not None:
        contact.company = capture.normalize_company(data["company"])
    for message in notes:
        capture._add_activity(db, lead, kind="updated", message=message, user_id=user.id)
    if not notes:
        capture._add_activity(db, lead, kind="updated", message="Lead updated.", user_id=user.id)
    db.commit()
    return _lead_out(_scoped_lead(db, client, lead.id, with_activities=True), include_activities=True)


@leads_router.post("/{lead_id}/activities", response_model=LeadOut)
def add_lead_activity(
    client_id: uuid.UUID,
    lead_id: uuid.UUID,
    payload: LeadActivityIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    lead = _scoped_lead(db, client, lead_id, with_activities=True)
    kind = payload.kind if payload.kind in {"note", "next_action"} else "note"
    capture._add_activity(db, lead, kind=kind, message=payload.message.strip(), user_id=user.id)
    db.commit()
    return _lead_out(_scoped_lead(db, client, lead.id, with_activities=True), include_activities=True)


@notifications_router.get("/notifications", response_model=list[LeadNotificationOut])
def list_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(
        select(LeadNotification)
        .options(selectinload(LeadNotification.lead).selectinload(Lead.contact))
        .where(LeadNotification.user_id == user.id, LeadNotification.agency_id == user.agency_id)
        .order_by(LeadNotification.created_at.desc())
        .limit(50)
    ).all()
    return [
        LeadNotificationOut(
            id=row.id,
            client_id=row.client_id,
            lead_id=row.lead_id,
            kind=row.kind,
            read_at=row.read_at,
            created_at=row.created_at,
            contact_name=(row.lead.contact.name if row.lead and row.lead.contact else ""),
            source=(row.lead.source if row.lead else ""),
        )
        for row in rows
    ]


@notifications_router.post("/notifications/{notification_id}/read", response_model=LeadNotificationOut)
def mark_notification_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.scalar(
        select(LeadNotification)
        .options(selectinload(LeadNotification.lead).selectinload(Lead.contact))
        .where(
            LeadNotification.id == notification_id,
            LeadNotification.user_id == user.id,
            LeadNotification.agency_id == user.agency_id,
        )
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    if not row.read_at:
        row.read_at = now_utc()
        db.commit()
        db.refresh(row)
    return LeadNotificationOut(
        id=row.id,
        client_id=row.client_id,
        lead_id=row.lead_id,
        kind=row.kind,
        read_at=row.read_at,
        created_at=row.created_at,
        contact_name=(row.lead.contact.name if row.lead and row.lead.contact else ""),
        source=(row.lead.source if row.lead else ""),
    )


@public_router.post("/{token}", status_code=status.HTTP_201_CREATED, dependencies=[Depends(lead_ingest_rate_limit)])
def public_ingest(token: str, payload: PublicLeadIn, db: Session = Depends(get_db)):
    settings = db.scalar(select(LeadCaptureSettings).where(LeadCaptureSettings.ingest_token == token))
    if not settings:
        raise HTTPException(status_code=404, detail="Lead capture endpoint not found")
    source = payload.source if payload.source in ("form", "webhook", "instagram", "facebook") else None
    if not source:
        raise HTTPException(status_code=400, detail="source must be form, webhook, instagram, or facebook")
    extra = dict(payload.extra or {})
    if payload.company:
        extra.setdefault("company", payload.company)
    raw = {
        "source": source,
        "name": payload.name,
        "email": payload.email,
        "phone": payload.phone,
        "company": payload.company,
        "channel_identifier": payload.channel_identifier,
        "extra": extra,
    }
    try:
        event = capture.capture(
            db,
            agency_id=settings.agency_id,
            client_id=settings.client_id,
            source=source,
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            company=payload.company,
            channel_identifier=payload.channel_identifier,
            extra=extra,
            payload=raw,
            trigger=source if source in ("form", "webhook") else "new_contact",
            mark_ingest=True,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if event.status == "skipped":
        return {"ok": True, "status": event.status, "detail": event.error_message, "lead_id": None}
    if event.status == "error":
        raise HTTPException(status_code=400, detail=event.error_message or "Lead capture failed")
    return {"ok": True, "status": event.status, "lead_id": str(event.lead_id) if event.lead_id else None}
