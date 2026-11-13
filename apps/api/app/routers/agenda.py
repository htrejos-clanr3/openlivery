"""Availability and appointments for one client."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Appointment, AvailabilityException, AvailabilityRule, Client, User
from ..services import agenda as service

router = APIRouter(prefix="/clients/{client_id}", tags=["Agenda"])


class RuleIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    slot_minutes: int = Field(default=60, ge=5, le=480)
    buffer_minutes: int = Field(default=0, ge=0, le=240)
    is_active: bool = True


class AvailabilityIn(BaseModel):
    timezone: str = "America/Bogota"
    rules: list[RuleIn] = Field(default_factory=list)


class ExceptionIn(BaseModel):
    exception_date: date
    is_closed: bool = True
    start_time: time | None = None
    end_time: time | None = None
    note: str = ""


class AppointmentIn(BaseModel):
    starts_at: datetime
    duration: int = Field(default=60, ge=5, le=480)
    contact_id: uuid.UUID | None = None
    lead_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    source: str = "panel"
    notes: str = ""
    idempotency_key: str | None = None


class AppointmentPatch(BaseModel):
    starts_at: datetime | None = None
    status: str | None = None
    reason: str = ""


def _client(db: Session, user: User, client_id: uuid.UUID) -> Client:
    client = db.get(Client, client_id)
    if client is None or client.agency_id != user.agency_id:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def _out(appointment: Appointment) -> dict:
    return {
        "id": str(appointment.id),
        "starts_at": appointment.starts_at.isoformat(),
        "ends_at": appointment.ends_at.isoformat(),
        "status": appointment.status,
        "source": appointment.source,
        "notes": appointment.notes,
        "meeting_url": appointment.meeting_url,
    }


@router.get("/availability")
def get_availability(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    rules = db.scalars(
        select(AvailabilityRule).where(
            AvailabilityRule.client_id == client.id, AvailabilityRule.agency_id == user.agency_id
        )
    ).all()
    exceptions = db.scalars(
        select(AvailabilityException).where(
            AvailabilityException.client_id == client.id, AvailabilityException.agency_id == user.agency_id
        )
    ).all()
    return {
        "timezone": client.timezone,
        "rules": [
            {
                "weekday": rule.weekday,
                "start_time": rule.start_time.isoformat(),
                "end_time": rule.end_time.isoformat(),
                "slot_minutes": rule.slot_minutes,
                "buffer_minutes": rule.buffer_minutes,
                "is_active": rule.is_active,
            }
            for rule in rules
        ],
        "exceptions": [
            {
                "exception_date": item.exception_date.isoformat(),
                "is_closed": item.is_closed,
                "start_time": item.start_time.isoformat() if item.start_time else None,
                "end_time": item.end_time.isoformat() if item.end_time else None,
                "note": item.note,
            }
            for item in exceptions
        ],
    }


@router.put("/availability")
def put_availability(
    client_id: uuid.UUID,
    payload: AvailabilityIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    client.timezone = payload.timezone
    db.query(AvailabilityRule).filter(
        AvailabilityRule.client_id == client.id, AvailabilityRule.agency_id == user.agency_id
    ).delete()
    for rule in payload.rules:
        db.add(
            AvailabilityRule(
                agency_id=user.agency_id,
                client_id=client.id,
                weekday=rule.weekday,
                start_time=rule.start_time,
                end_time=rule.end_time,
                slot_minutes=rule.slot_minutes,
                buffer_minutes=rule.buffer_minutes,
                is_active=rule.is_active,
            )
        )
    db.commit()
    return get_availability(client_id, db, user)


@router.post("/availability/exceptions")
def add_exception(
    client_id: uuid.UUID,
    payload: ExceptionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    db.add(
        AvailabilityException(
            agency_id=user.agency_id,
            client_id=client.id,
            exception_date=payload.exception_date,
            is_closed=payload.is_closed,
            start_time=payload.start_time,
            end_time=payload.end_time,
            note=payload.note[:240],
        )
    )
    db.commit()
    return {"ok": True}


@router.get("/availability/slots")
def list_slots(
    client_id: uuid.UUID,
    date_from: datetime,
    date_to: datetime,
    duration: int = 60,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    slots = service.available_slots(db, client, date_from, date_to, duration=duration)
    return {"slots": [slot.isoformat() for slot in slots]}


@router.get("/appointments")
def list_appointments(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    rows = db.scalars(
        select(Appointment)
        .where(Appointment.client_id == client.id, Appointment.agency_id == user.agency_id)
        .order_by(Appointment.starts_at.desc())
        .limit(200)
    ).all()
    return [_out(row) for row in rows]


@router.post("/appointments")
def create_appointment(
    client_id: uuid.UUID,
    payload: AppointmentIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    try:
        appointment = service.book(
            db,
            client,
            payload.starts_at,
            duration=payload.duration,
            contact_id=payload.contact_id,
            lead_id=payload.lead_id,
            agent_id=payload.agent_id,
            source=payload.source,
            notes=payload.notes,
            idempotency_key=payload.idempotency_key,
            actor_user_id=user.id,
        )
    except service.AgendaError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _out(appointment)


@router.patch("/appointments/{appointment_id}")
def patch_appointment(
    client_id: uuid.UUID,
    appointment_id: uuid.UUID,
    payload: AppointmentPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _client(db, user, client_id)
    appointment = db.get(Appointment, appointment_id)
    if appointment is None or appointment.client_id != client.id or appointment.agency_id != user.agency_id:
        raise HTTPException(status_code=404, detail="Appointment not found")
    try:
        if payload.starts_at is not None:
            appointment = service.reschedule(db, appointment, payload.starts_at, actor_user_id=user.id)
        elif payload.status == "cancelled":
            appointment = service.cancel(db, appointment, payload.reason, actor_user_id=user.id)
    except service.AgendaError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _out(appointment)
