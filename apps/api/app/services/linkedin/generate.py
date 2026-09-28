"""Generate LinkedIn copy. Never publishes to LinkedIn."""

from __future__ import annotations

import json
import re

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ...models import Client
from ..carousels import CHAT_MODELS, _openai_chat_json, resolve_chat_credentials
from . import DATA_DIR
from .detect import run as detect_run
from .humanize import humanize, load_lexicon

HOOKS_PATH = DATA_DIR / "hooks.json"
RUBRIC_PATH = DATA_DIR / "rubric.json"
SLOP_PATH = DATA_DIR / "slop.json"


def load_hooks() -> dict:
    return json.loads(HOOKS_PATH.read_text(encoding="utf-8"))


def load_rubric() -> dict:
    return json.loads(RUBRIC_PATH.read_text(encoding="utf-8"))


def load_slop() -> dict:
    return load_lexicon(str(SLOP_PATH))


def score_text(text: str) -> dict:
    lex = load_slop()
    results, overall, verdict = detect_run(text, lex)
    return {
        "checks": {name: {"score": round(score, 1), "detail": detail} for name, (score, detail) in results.items()},
        "human_score": round(overall, 1),
        "verdict": verdict,
    }


def clean_text(text: str) -> tuple[str, dict, dict]:
    lex = load_slop()
    cleaned, report = humanize(text, lex)
    cleaned = cleaned.strip()
    return cleaned, report, score_text(cleaned)


def _extract_json(text: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", text)
    raw = match.group(0) if match else text
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="AI returned invalid LinkedIn JSON") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="AI returned unexpected shape")
    return data


def _voice_block(client: Client, voice_notes: str) -> str:
    return (
        f"Client: {client.name}\n"
        f"Industry: {client.industry}\n"
        f"Description: {client.description or ''}\n"
        f"Context: {client.general_context or ''}\n"
        f"Brand voice: {client.brand_voice or 'clear and specific'}\n"
        f"Voice notes:\n{voice_notes.strip() or '(none — infer from brand, do not invent a persona)'}\n"
    )


def _fallback_post(idea: str, hooks: list[dict]) -> dict:
    by_id = {h["id"]: h for h in hooks}
    picks = [by_id[i] for i in (17, 2, 21) if i in by_id] or hooks[:3]
    lines = []
    for hook in picks:
        lines.append(
            {
                "id": hook["id"],
                "name": hook["name"],
                "line": hook["example"],
                "why": hook["best_for"],
            }
        )
    draft = (
        f"{lines[0]['line']}\n\n"
        f"{idea.strip()}\n\n"
        "If a number is missing, leave {{your number}} rather than inventing one.\n\n"
        "What would you change first?"
    )
    return {"hooks": lines, "chosen_hook_id": lines[0]["id"], "draft": draft, "source": "fallback"}


async def generate_post(
    db: Session,
    *,
    client: Client,
    idea: str,
    voice_notes: str = "",
    language: str = "es",
) -> dict:
    pack = load_hooks()
    hooks = pack["hooks"]
    idea = idea.strip()
    if len(idea) < 8:
        raise HTTPException(status_code=400, detail="Give one specific true thing that happened")
    creds = resolve_chat_credentials(db, client.agency_id)
    payload: dict
    if not creds:
        payload = _fallback_post(idea, hooks)
    else:
        provider, base_url, api_key = creds
        model = CHAT_MODELS.get(provider, "deepseek-chat")
        catalog = json.dumps(
            [{"id": h["id"], "name": h["name"], "template": h["template"], "best_for": h["best_for"], "trap": h["trap"]} for h in hooks],
            ensure_ascii=False,
        )
        system = (
            "You write LinkedIn posts that sound like a specific person. "
            "Never fabricate metrics, clients or outcomes. If a number is needed and unknown, use {{your number}}. "
            "No outbound links in the body. Max 3 hashtags. Never 'Thoughts?' or 'Agree?'. "
            "Return ONLY JSON."
        )
        user = f"""Language: {language}

Voice:
{_voice_block(client, voice_notes)}

Idea:
{idea}

Hook catalog:
{catalog}

Rules from the catalog: {pack.get("note")}
{chr(10).join(pack.get("rules") or [])}

Return:
{{
  "hooks": [
    {{"id": 17, "name": "Time Anchor", "line": "...", "why": "one sentence"}}
  ],
  "chosen_hook_id": 17,
  "draft": "full post with blank lines between short paragraphs"
}}
Give exactly three different hook formulas. Draft the full post on chosen_hook_id.
Length 900-1300 characters when the idea supports it. Line 1 must stand alone under 140 characters.
"""
        try:
            raw, _usage = _openai_chat_json(
                base_url=base_url, api_key=api_key, model=model, system=system, user=user
            )
            payload = _extract_json(raw)
            payload["source"] = provider
        except HTTPException:
            payload = _fallback_post(idea, hooks)
    draft = str(payload.get("draft") or "").strip()
    cleaned, report, panel = clean_text(draft)
    payload["draft"] = cleaned
    payload["humanize"] = {
        "stripped": sum(item.get("count", 0) for bucket in ("invisible", "typographic", "lexical") for item in report.get(bucket, [])),
        "structures": report.get("structures") or [],
        "panel": panel,
    }
    payload["copy_ready"] = cleaned
    payload["post_at_hint"] = (
        "Revisa el texto exacto. Publícalo con la API oficial o cópialo en LinkedIn."
        if language.startswith("es")
        else "Review the exact text. Publish it through the official API or copy it into LinkedIn."
    )
    return payload


def score_profile_heuristic(pasted: str) -> dict:
    rubric = load_rubric()
    text = pasted.strip()
    lower = text.lower()
    scores: list[dict] = []
    mapping = {
        "headline": 12 if ("|" in text or "help" in lower or "ayudo" in lower) and len(text) > 40 else 4,
        "about_open": 2 if "passionate about" in lower or "apasionad" in lower else (8 if len(text) > 80 else 3),
        "about_body": 8 if "you" in lower or "tú" in lower or "tu " in lower else 3,
        "featured": 2,
        "banner": 2,
        "photo": 2,
        "current_role": 6 if re.search(r"\d", text) else 3,
        "experience_depth": 3,
        "skills": 2,
        "recommendations": 2,
        "activity": 2,
        "contact": 4 if "@" in text or "http" in lower else 1,
    }
    total = 0
    for item in rubric["items"]:
        pts = min(item["points"], mapping.get(item["id"], 2))
        total += pts
        scores.append({"id": item["id"], "points": item["points"], "score": pts, "full_marks": item["full_marks"]})
    return {"total": total, "max": rubric["total"], "items": scores, "source": "heuristic"}


async def rewrite_profile(
    db: Session,
    *,
    client: Client,
    pasted: str,
    voice_notes: str = "",
    language: str = "es",
) -> dict:
    audit = score_profile_heuristic(pasted)
    creds = resolve_chat_credentials(db, client.agency_id)
    if not creds:
        headline = f"{client.name} | {client.industry or 'resultado claro'}"[:220]
        about = (
            f"Si {client.industry or 'tu negocio'} se traba en el siguiente paso, aquí está el arreglo.\n\n"
            f"{(client.description or idea_safe(client))[:400]}\n\n"
            "Escribe y agenda. No inventes cifras: {{your number}}."
        )
        cleaned, _, panel = clean_text(about)
        return {
            "audit": audit,
            "headline": headline,
            "about": cleaned,
            "featured": ["Mejor post", "Prueba (caso o número real)", "Cómo contactarte"],
            "humanize": {"panel": panel},
            "source": "fallback",
            "copy_note": "Paste into LinkedIn. Graph does not let apps write the profile.",
        }
    provider, base_url, api_key = creds
    model = CHAT_MODELS.get(provider, "deepseek-chat")
    system = "Rewrite a LinkedIn profile. Never invent metrics. Return ONLY JSON."
    user = f"""Language: {language}
Voice:
{_voice_block(client, voice_notes)}
Current profile paste:
{pasted[:6000]}
Rubric:
{json.dumps(load_rubric(), ensure_ascii=False)}
Heuristic audit:
{json.dumps(audit, ensure_ascii=False)}
Return:
{{
  "headline": "...",
  "about": "...",
  "current_role_bullets": ["..."],
  "featured": ["best post", "proof asset", "contact path"],
  "banner_line": "..."
}}
Headline uses who you help + outcome + one proof, up to 220 characters.
About: first two lines name the reader's problem. Second person. Under 1400 characters.
"""
    try:
        raw, _usage = _openai_chat_json(
            base_url=base_url, api_key=api_key, model=model, system=system, user=user
        )
        payload = _extract_json(raw)
        payload["source"] = provider
    except HTTPException:
        payload = {"headline": f"{client.name} | {client.industry}", "about": pasted[:800], "source": "fallback"}
    about = str(payload.get("about") or "")
    cleaned, _, panel = clean_text(about)
    payload["about"] = cleaned
    payload["audit"] = audit
    payload["humanize"] = {"panel": panel}
    payload["copy_note"] = "Paste into LinkedIn. OpenLivery does not write the live profile."
    return payload


def idea_safe(client: Client) -> str:
    return client.general_context or client.description or client.name
