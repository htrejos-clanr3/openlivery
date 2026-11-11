"""A minimal MCP-style endpoint so an assistant can operate Fast Livery.

JSON-RPC 2.0 over HTTP. Same session auth as the rest of the API: no token lives
outside the platform.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Client, Contact, Lead, LeadStage, User, now_utc

router = APIRouter(prefix="/mcp", tags=["MCP"])

TOOLS = [
    {
        "name": "list_clients",
        "description": "List the agency clients with their id.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_leads",
        "description": "List scored leads of one client, hottest first.",
        "inputSchema": {
            "type": "object",
            "properties": {"client_id": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["client_id"],
        },
    },
    {
        "name": "get_lead",
        "description": "Full detail of one lead: contact, score, notes and next action.",
        "inputSchema": {
            "type": "object",
            "properties": {"lead_id": {"type": "string"}},
            "required": ["lead_id"],
        },
    },
    {
        "name": "log_contact",
        "description": "Record that someone contacted a lead and what happened.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string"},
                "note": {"type": "string"},
                "channel": {"type": "string"},
            },
            "required": ["lead_id", "note"],
        },
    },
    {
        "name": "schedule_followup",
        "description": "Set the next action for a lead, with an optional date.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string"},
                "next_action": {"type": "string"},
            },
            "required": ["lead_id", "next_action"],
        },
    },
]


def _lead(db: Session, user: User, lead_id: str) -> Lead | None:
    try:
        value = uuid.UUID(lead_id)
    except ValueError:
        return None
    return db.scalars(
        select(Lead).where(Lead.id == value, Lead.agency_id == user.agency_id)
    ).first()


def _call(name: str, args: dict, db: Session, user: User):
    if name == "list_clients":
        rows = db.scalars(select(Client).where(Client.agency_id == user.agency_id)).all()
        return [{"id": str(row.id), "name": row.name} for row in rows]

    if name == "list_leads":
        rows = db.execute(
            select(Lead, Contact, LeadStage)
            .join(Contact, Contact.id == Lead.contact_id)
            .outerjoin(LeadStage, LeadStage.id == Lead.stage_id)
            .where(Lead.agency_id == user.agency_id, Lead.client_id == uuid.UUID(args["client_id"]))
            .order_by(Lead.score.desc().nullslast())
            .limit(int(args.get("limit", 25)))
        ).all()
        return [
            {
                "id": str(lead.id),
                "name": contact.name or contact.phone,
                "phone": contact.phone,
                "score": lead.score,
                "stage": stage.name if stage else None,
                "next_action": lead.next_action,
            }
            for lead, contact, stage in rows
        ]

    if name == "get_lead":
        lead = _lead(db, user, args["lead_id"])
        if lead is None:
            raise ValueError("lead not found")
        contact = db.get(Contact, lead.contact_id)
        return {
            "id": str(lead.id),
            "name": contact.name if contact else None,
            "phone": contact.phone if contact else None,
            "score": lead.score,
            "source": lead.source,
            "notes": lead.notes,
            "next_action": lead.next_action,
            "last_activity_at": lead.last_activity_at.isoformat() if lead.last_activity_at else None,
        }

    if name == "log_contact":
        lead = _lead(db, user, args["lead_id"])
        if lead is None:
            raise ValueError("lead not found")
        stamp = now_utc().strftime("%Y-%m-%d %H:%M")
        channel = args.get("channel") or "manual"
        line = f"{stamp} · {channel}: {args['note']}"
        lead.notes = ((lead.notes + "\n") if lead.notes else "") + line
        lead.last_activity_at = now_utc()
        db.commit()
        return {"ok": True, "notes": lead.notes}

    if name == "schedule_followup":
        lead = _lead(db, user, args["lead_id"])
        if lead is None:
            raise ValueError("lead not found")
        lead.next_action = args["next_action"][:240]
        lead.last_activity_at = now_utc()
        db.commit()
        return {"ok": True, "next_action": lead.next_action}

    raise ValueError(f"unknown tool: {name}")


@router.post("")
async def rpc(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payload = await request.json()
    method = payload.get("method")
    rid = payload.get("id")
    params = payload.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "fast-livery", "version": "1.0.0"},
                "capabilities": {"tools": {}},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments") or {}
        try:
            result = _call(name, args, db, user)
            return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": str(result)}]}}
        except Exception as exc:  # noqa: BLE001
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32000, "message": str(exc)[:200]}}

    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"unknown method: {method}"}}
