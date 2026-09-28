"""DeepSeek-native automations: lead clean/score, documents, reminder/onboarding copy.

Does not integrate HubSpot, Slack, Calendly, or Asana — those stay outside this slice.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from .providers import resolve_provider_credentials

DEEPSEEK_MODEL = "deepseek-chat"
HOT_MIN = 7
WARM_MIN = 4


def require_deepseek(db: Session, agency_id) -> tuple[str, str]:
    creds = resolve_provider_credentials(db, agency_id, "deepseek")
    if not creds:
        raise HTTPException(
            status_code=400,
            detail="Configure a DeepSeek API key in Settings to run these automations.",
        )
    return creds


def score_from_fields(
    *,
    budget: float | None,
    timeline_days: int | None,
    employees: int | None,
    is_decision_maker: bool | None,
) -> dict:
    breakdown = {
        "budget": 3 if (budget or 0) >= 10_000 else 0,
        "timeline": 2 if timeline_days is not None and timeline_days <= 30 else 0,
        "employees": 2 if (employees or 0) >= 50 else 0,
        "decision_maker": 3 if is_decision_maker else 0,
    }
    total = sum(breakdown.values())
    if total >= HOT_MIN:
        band, routing = "hot", "senior_sales"
    elif total >= WARM_MIN:
        band, routing = "warm", "follow_up"
    else:
        band, routing = "cold", "archive"
    return {"score": total, "band": band, "routing": routing, "breakdown": breakdown}


def _parse_json_object(text: str) -> dict:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="DeepSeek returned invalid JSON.") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="DeepSeek JSON must be an object.")
    return data


async def deepseek_json(*, base_url: str, api_key: str, system: str, user: str) -> dict:
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": DEEPSEEK_MODEL,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail=f"DeepSeek error: {response.text[:300]}")
    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="Unexpected DeepSeek response.") from exc
    return _parse_json_object(content or "{}")


def _payload_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload.strip()
    return json.dumps(payload, ensure_ascii=False, indent=2)


async def normalize_lead(db: Session, agency_id, payload: Any) -> dict:
    base_url, api_key = require_deepseek(db, agency_id)
    system = (
        "You extract a sales lead from messy form data. Reply with JSON only, keys: "
        "name, email, phone, company, role, budget_usd (number or null), "
        "timeline_days (integer or null), employees (integer or null), "
        "is_decision_maker (boolean or null), notes, cleaned (object of tidy fields). "
        "Use null when unknown. Do not invent emails. Language of notes: Spanish if the input is Spanish."
    )
    extracted = await deepseek_json(
        base_url=base_url,
        api_key=api_key,
        system=system,
        user=_payload_text(payload),
    )
    return extracted


async def score_lead(db: Session, agency_id, payload: Any) -> dict:
    extracted = await normalize_lead(db, agency_id, payload)
    scored = score_from_fields(
        budget=_as_float(extracted.get("budget_usd")),
        timeline_days=_as_int(extracted.get("timeline_days")),
        employees=_as_int(extracted.get("employees")),
        is_decision_maker=extracted.get("is_decision_maker") is True,
    )
    reasons = {
        "hot": "Lead caliente → vendedores senior (7+ puntos).",
        "warm": "Lead tibio → seguimiento (4–6 puntos).",
        "cold": "Lead frío → archivo (<4 puntos).",
    }
    return {
        "lead": extracted,
        **scored,
        "reason": reasons[scored["band"]],
        "rubric": {
            "budget_gte_10000": "+3",
            "timeline_lte_30_days": "+2",
            "employees_gte_50": "+2",
            "decision_maker": "+3",
        },
    }


def fill_template(template: str, variables: dict[str, Any]) -> tuple[str, list[str]]:
    missing: list[str] = []

    def repl(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        if key in variables and variables[key] not in (None, ""):
            return str(variables[key])
        missing.append(key)
        return match.group(0)

    filled = re.sub(r"\{\{\s*([^}]+?)\s*\}\}", repl, template)
    return filled, sorted(set(missing))


async def render_document(
    db: Session,
    agency_id,
    *,
    template: str,
    variables: dict[str, Any],
    doc_type: str,
) -> dict:
    filled, missing = fill_template(template, variables)
    base_url, api_key = require_deepseek(db, agency_id)
    system = (
        "You write a professional business document in the same language as the template. "
        "Reply JSON keys: title, body_markdown. Keep every fact from the filled template. "
        "Do not invent prices, names, or legal clauses that are not in the input. "
        "If {{placeholders}} remain, keep them visible."
    )
    user = json.dumps(
        {"doc_type": doc_type, "filled_template": filled, "variables": variables, "missing": missing},
        ensure_ascii=False,
    )
    generated = await deepseek_json(base_url=base_url, api_key=api_key, system=system, user=user)
    return {
        "filled_template": filled,
        "missing_variables": missing,
        "title": generated.get("title") or doc_type,
        "body_markdown": generated.get("body_markdown") or filled,
        "doc_type": doc_type,
    }


async def email_copy(
    db: Session,
    agency_id,
    *,
    kind: str,
    context: dict[str, Any],
) -> dict:
    allowed = {"reminder_24h", "reminder_1h", "followup", "onboarding"}
    if kind not in allowed:
        raise HTTPException(status_code=400, detail="Unknown copy kind")
    base_url, api_key = require_deepseek(db, agency_id)
    labels = {
        "reminder_24h": "Reminder email 24 hours before a scheduled call.",
        "reminder_1h": "Reminder email 1 hour before a scheduled call.",
        "followup": "Follow-up email after the call.",
        "onboarding": "Client onboarding welcome email after they sign or pay.",
    }
    system = (
        "You write concise operational email copy. Reply JSON keys: subject, body. "
        "Spanish if the context is Spanish. No invented URLs. Short, specific, no fluff."
    )
    user = json.dumps({"kind": kind, "instruction": labels[kind], "context": context}, ensure_ascii=False)
    generated = await deepseek_json(base_url=base_url, api_key=api_key, system=system, user=user)
    return {
        "kind": kind,
        "subject": generated.get("subject") or "",
        "body": generated.get("body") or "",
    }


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
