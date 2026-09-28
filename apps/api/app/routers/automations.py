"""DeepSeek automations: per-user runs (lead score, documents, copy)."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, UserAutomationRun, now_utc
from ..schemas_automations import (
    AutomationRunOut,
    AutomationsStatusOut,
    DocumentIn,
    EmailCopyIn,
    LeadPayloadIn,
)
from ..services import automations as auto
from ..services.providers import resolve_provider_credentials


router = APIRouter(prefix="/automations", tags=["Automations"])


def _run_out(row: UserAutomationRun) -> AutomationRunOut:
    return AutomationRunOut.model_validate(row)


def _json_object(value: dict) -> dict:
    dumped = json.loads(json.dumps(value, default=str))
    return dumped if isinstance(dumped, dict) else {"value": dumped}


def _save_run(db: Session, user: User, kind: str, payload: dict, result: dict) -> UserAutomationRun:
    row = UserAutomationRun(
        agency_id=user.agency_id,
        user_id=user.id,
        kind=kind,
        payload=_json_object(payload),
        result=_json_object(result),
        created_at=now_utc(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _get_own_run(db: Session, user: User, run_id: uuid.UUID) -> UserAutomationRun:
    row = (
        db.query(UserAutomationRun)
        .filter(
            UserAutomationRun.id == run_id,
            UserAutomationRun.user_id == user.id,
            UserAutomationRun.agency_id == user.agency_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Automation run not found")
    return row


@router.get("/status", response_model=AutomationsStatusOut)
def status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    configured = resolve_provider_credentials(db, user.agency_id, "deepseek") is not None
    return AutomationsStatusOut(
        deepseek_configured=configured,
        model=auto.DEEPSEEK_MODEL,
        user_id=str(user.id),
        user_name=user.name,
    )


@router.get("/runs", response_model=list[AutomationRunOut])
def list_runs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(UserAutomationRun)
        .filter(UserAutomationRun.user_id == user.id, UserAutomationRun.agency_id == user.agency_id)
        .order_by(UserAutomationRun.created_at.desc())
        .limit(50)
        .all()
    )
    return [_run_out(row) for row in rows]


@router.get("/runs/{run_id}", response_model=AutomationRunOut)
def get_run(run_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _run_out(_get_own_run(db, user, run_id))


@router.post("/normalize", response_model=AutomationRunOut)
async def normalize(payload: LeadPayloadIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await auto.normalize_lead(db, user.agency_id, payload.payload)
    return _run_out(_save_run(db, user, "normalize", {"payload": payload.payload}, result))


@router.post("/score", response_model=AutomationRunOut)
async def score(payload: LeadPayloadIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await auto.score_lead(db, user.agency_id, payload.payload)
    return _run_out(_save_run(db, user, "score", {"payload": payload.payload}, result))


@router.post("/document", response_model=AutomationRunOut)
async def document(payload: DocumentIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await auto.render_document(
        db,
        user.agency_id,
        template=payload.template,
        variables=payload.variables,
        doc_type=payload.doc_type,
    )
    return _run_out(
        _save_run(
            db,
            user,
            "document",
            {"template": payload.template, "variables": payload.variables, "doc_type": payload.doc_type},
            result,
        )
    )


@router.post("/copy", response_model=AutomationRunOut)
async def copy(payload: EmailCopyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await auto.email_copy(db, user.agency_id, kind=payload.kind, context=payload.context)
    return _run_out(_save_run(db, user, "copy", {"kind": payload.kind, "context": payload.context}, result))
