"""Availability and booking. Times are UTC in the database, local in the API."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import (
    Appointment,
    AppointmentAudit,
    AvailabilityException,
    AvailabilityRule,
    Client,
    now_utc,
)


class AgendaError(Exception):
    """Raised when a slot cannot be booked."""


def client_zone(client: Client) -> ZoneInfo:
    return ZoneInfo(client.timezone or "America/Bogota")


def _windows_for_day(
    day: date,
    rules: list[AvailabilityRule],
    exceptions: list[AvailabilityException],
) -> list[tuple[time, time, int, int]]:
    """Return the (start, end, slot_minutes, buffer_minutes) windows for one day."""
    for exception in exceptions:
        if exception.exception_date == day and exception.is_closed:
            return []
        if exception.exception_date == day and not exception.is_closed and exception.start_time and exception.end_time:
            rule = next((r for r in rules if r.weekday == day.weekday()), None)
            return [
                (
                    exception.start_time,
                    exception.end_time,
                    rule.slot_minutes if rule else 60,
                    rule.buffer_minutes if rule else 0,
                )
            ]
    return [
        (rule.start_time, rule.end_time, rule.slot_minutes, rule.buffer_minutes)
        for rule in rules
        if rule.weekday == day.weekday() and rule.is_active
    ]


def _slots_in_window(
    day: date,
    start: time,
    end: time,
    slot_minutes: int,
    buffer_minutes: int,
    zone: ZoneInfo,
) -> list[tuple[datetime, datetime]]:
    cursor = datetime.combine(day, start, tzinfo=zone)
    limit = datetime.combine(day, end, tzinfo=zone)
    slots: list[tuple[datetime, datetime]] = []
    while cursor + timedelta(minutes=slot_minutes) <= limit:
        slots.append((cursor, cursor + timedelta(minutes=slot_minutes)))
        cursor = cursor + timedelta(minutes=slot_minutes + buffer_minutes)
    return slots


def _free(slot: tuple[datetime, datetime], busy: list[tuple[datetime, datetime]]) -> bool:
    start, end = slot
    return all(end <= other_start or start >= other_end for other_start, other_end in busy)


def available_slots(
    db: Session,
    client: Client,
    start: datetime,
    end: datetime,
    duration: int | None = None,
) -> list[datetime]:
    """Free slot starts between start and end, in the client time zone."""
    zone = client_zone(client)
    rules = list(
        db.scalars(
            select(AvailabilityRule).where(
                AvailabilityRule.client_id == client.id,
                AvailabilityRule.agency_id == client.agency_id,
            )
        )
    )
    exceptions = list(
        db.scalars(
            select(AvailabilityException).where(
                AvailabilityException.client_id == client.id,
                AvailabilityException.agency_id == client.agency_id,
            )
        )
    )
    busy = [
        (appointment.starts_at, appointment.ends_at)
        for appointment in db.scalars(
            select(Appointment).where(
                Appointment.client_id == client.id,
                Appointment.agency_id == client.agency_id,
                Appointment.status.in_(["scheduled", "rescheduled"]),
                Appointment.ends_at > start,
                Appointment.starts_at < end,
            )
        )
    ]

    results: list[datetime] = []
    day = start.astimezone(zone).date()
    last_day = end.astimezone(zone).date()
    while day <= last_day:
        for window in _windows_for_day(day, rules, exceptions):
            slot_minutes = duration or window[2]
            for slot in _slots_in_window(day, window[0], window[1], slot_minutes, window[3], zone):
                if slot[0] < start or slot[1] > end:
                    continue
                if _free(slot, busy):
                    results.append(slot[0].astimezone(ZoneInfo("UTC")))
        day += timedelta(days=1)
    return sorted(results)


def book(
    db: Session,
    client: Client,
    starts_at: datetime,
    *,
    duration: int = 60,
    contact_id=None,
    lead_id=None,
    agent_id=None,
    source: str = "panel",
    notes: str = "",
    idempotency_key: str | None = None,
    actor_user_id=None,
) -> Appointment:
    """Book a slot. Raises AgendaError when the slot is taken or outside hours."""
    if starts_at.tzinfo is None:
        raise AgendaError("starts_at must be timezone aware")
    slot_start = starts_at.astimezone(ZoneInfo("UTC"))
    slot_end = slot_start + timedelta(minutes=duration)

    free = available_slots(db, client, slot_start, slot_end, duration=duration)
    if slot_start not in free:
        raise AgendaError("slot is not available")

    appointment = Appointment(
        agency_id=client.agency_id,
        client_id=client.id,
        contact_id=contact_id,
        lead_id=lead_id,
        agent_id=agent_id,
        starts_at=slot_start,
        ends_at=slot_end,
        source=source,
        notes=notes,
        idempotency_key=idempotency_key,
    )
    db.add(appointment)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise AgendaError("duplicate booking") from None

    db.add(
        AppointmentAudit(
            appointment_id=appointment.id,
            actor_user_id=actor_user_id,
            action="created",
            payload={"starts_at": slot_start.isoformat(), "source": source},
        )
    )
    db.commit()
    return appointment


def reschedule(db: Session, appointment: Appointment, new_start: datetime, *, actor_user_id=None) -> Appointment:
    duration = int((appointment.ends_at - appointment.starts_at).total_seconds() // 60)
    client = db.get(Client, appointment.client_id)
    if client is None:
        raise AgendaError("client not found")
    appointment.status = "cancelled"
    db.flush()
    replacement = book(
        db,
        client,
        new_start,
        duration=duration,
        contact_id=appointment.contact_id,
        lead_id=appointment.lead_id,
        agent_id=appointment.agent_id,
        source="rescheduled",
        actor_user_id=actor_user_id,
    )
    db.add(
        AppointmentAudit(
            appointment_id=appointment.id,
            actor_user_id=actor_user_id,
            action="rescheduled",
            payload={"moved_to": replacement.id.hex, "new_start": replacement.starts_at.isoformat()},
        )
    )
    db.commit()
    return replacement


def cancel(db: Session, appointment: Appointment, reason: str = "", *, actor_user_id=None) -> Appointment:
    appointment.status = "cancelled"
    appointment.cancelled_reason = reason[:240]
    appointment.updated_at = now_utc()
    db.add(
        AppointmentAudit(
            appointment_id=appointment.id,
            actor_user_id=actor_user_id,
            action="cancelled",
            payload={"reason": reason[:240]},
        )
    )
    db.commit()
    return appointment
