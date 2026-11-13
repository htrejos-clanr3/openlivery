"""What the agent needs to reason about the agenda before it speaks.

The graph never reads availability straight from the database: it asks these
functions, which return a small, explainable structure. That keeps the prompt
short and the decision auditable.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..models import Client
from .agenda import AgendaError, available_slots, book, client_zone


def evaluate_agenda(db: Session, client: Client, horizon_days: int = 7) -> dict:
    """Summary the agent reads before offering an appointment."""
    zone = client_zone(client)
    now = datetime.now(zone)
    until = now + timedelta(days=horizon_days)
    slots = available_slots(db, client, now, until)

    by_day: dict[str, list[str]] = {}
    for slot in slots:
        local = slot.astimezone(zone)
        by_day.setdefault(local.date().isoformat(), []).append(local.strftime("%H:%M"))

    return {
        "timezone": client.timezone,
        "now_local": now.isoformat(),
        "horizon_days": horizon_days,
        "total_free": len(slots),
        "next_free": slots[0].astimezone(zone).isoformat() if slots else None,
        "days": [
            {"date": day, "times": times, "count": len(times)}
            for day, times in sorted(by_day.items())
        ],
        "has_availability": bool(slots),
    }


def list_slots_tool(db: Session, client: Client, horizon_days: int = 7) -> dict:
    """Tool result for the graph: the agenda digest plus the raw slot ISO strings."""
    digest = evaluate_agenda(db, client, horizon_days)
    zone = client_zone(client)
    now = datetime.now(zone)
    slots = available_slots(db, client, now, now + timedelta(days=horizon_days))
    digest["slots"] = [slot.isoformat() for slot in slots[:20]]
    return digest


def book_slot_tool(
    db: Session,
    client: Client,
    starts_at: datetime,
    *,
    duration: int = 60,
    contact_id=None,
    lead_id=None,
    conversation_id: str = "",
) -> dict:
    """Tool result for the graph. Only a slot the agent was offered may be booked."""
    try:
        appointment = book(
            db,
            client,
            starts_at,
            duration=duration,
            contact_id=contact_id,
            lead_id=lead_id,
            source="agent",
            idempotency_key=f"agent:{conversation_id}:{starts_at.isoformat()}" if conversation_id else None,
        )
    except AgendaError as exc:
        return {
            "ok": False,
            "reason": str(exc),
            "message": (
                "Ese horario ya no está disponible. Ofrece otro de los huecos libres."
                if "not available" in str(exc)
                else "No se pudo reservar. Pide disculpas y ofrece un enlace de contacto."
            ),
        }
    zone = client_zone(client)
    return {
        "ok": True,
        "appointment_id": str(appointment.id),
        "starts_at_local": appointment.starts_at.astimezone(zone).isoformat(),
        "ends_at_local": appointment.ends_at.astimezone(zone).isoformat(),
        "timezone": client.timezone,
    }
