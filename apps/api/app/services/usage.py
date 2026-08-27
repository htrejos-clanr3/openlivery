import uuid

from sqlalchemy.orm import Session

from ..models import UsageRecord
from .ai import Completion

# USD per 1M tokens (list prices; image models bill output as image tokens).
# Update if OpenAI/DeepSeek change public rates.
TOKEN_RATES_USD_PER_MILLION: dict[str, tuple[float, float]] = {
    "gpt-image-1-mini": (2.00, 8.00),
    "gpt-image-1": (5.00, 40.00),
    "gpt-image-1.5": (5.00, 32.00),
    "deepseek-chat": (0.28, 0.42),
    "gpt-4.1-mini": (0.40, 1.60),
    "kimi-k2.5": (0.60, 2.50),
    "qwen-plus": (0.40, 1.20),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    if (input_tokens or 0) <= 0 and (output_tokens or 0) <= 0:
        return 0.0
    rates = TOKEN_RATES_USD_PER_MILLION.get(model) or TOKEN_RATES_USD_PER_MILLION.get(model.split("/")[-1])
    if not rates:
        lowered = (model or "").lower()
        if lowered.startswith("flux") or lowered.startswith("x/") or lowered == "placeholder":
            rates = (0.0, 0.0)
        else:
            rates = (5.00, 40.00) if "image" in lowered else (0.50, 1.50)
    inp, out = rates
    return round((input_tokens / 1_000_000) * inp + (output_tokens / 1_000_000) * out, 6)


def usage_entry(
    *,
    kind: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    label: str | None = None,
) -> dict:
    row = {
        "kind": kind,
        "provider": provider,
        "model": model,
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "estimated_usd": estimate_cost_usd(model, int(input_tokens or 0), int(output_tokens or 0)),
        "count": 1,
    }
    if label:
        row["label"] = label
    return row


def summarize_usage(rows: list[dict]) -> dict:
    items = []
    for row in rows:
        inp = int(row.get("input_tokens") or 0)
        out = int(row.get("output_tokens") or 0)
        kind = row.get("kind") or ""
        # Keep local image rows even at 0 tokens so the carousel usage table
        # still shows Flux/Ollama/placeholder generations at $0.
        if inp <= 0 and out <= 0 and kind != "image":
            continue
        items.append(
            {
                "kind": row.get("kind") or "",
                "provider": row.get("provider") or "",
                "model": row.get("model") or "",
                "input_tokens": inp,
                "output_tokens": out,
                "estimated_usd": float(row.get("estimated_usd") or estimate_cost_usd(row.get("model") or "", inp, out)),
                "count": int(row.get("count") or 1),
                "label": row.get("label") or None,
            }
        )
    return {
        "items": items,
        "input_tokens": sum(i["input_tokens"] for i in items),
        "output_tokens": sum(i["output_tokens"] for i in items),
        "estimated_usd": round(sum(float(i["estimated_usd"]) for i in items), 6),
    }


def persist_usage_rows(db: Session, agency_id: uuid.UUID, rows: list[dict]) -> dict:
    summary = summarize_usage(rows)
    for row in summary.get("items") or []:
        record_tokens(
            db,
            agency_id,
            None,
            row["provider"],
            row["model"],
            row["input_tokens"],
            row["output_tokens"],
        )
    return summary


def record_usage(db: Session, agency_id: uuid.UUID, agent_id: uuid.UUID | None, provider: str, model: str, completion: Completion) -> None:
    """Store token usage for a completion. The caller owns the commit."""
    record_tokens(db, agency_id, agent_id, provider, model, completion.input_tokens, completion.output_tokens)


def record_tokens(
    db: Session,
    agency_id: uuid.UUID,
    agent_id: uuid.UUID | None,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    if (input_tokens or 0) <= 0 and (output_tokens or 0) <= 0:
        return
    db.add(
        UsageRecord(
            agency_id=agency_id,
            agent_id=agent_id,
            provider=provider,
            model=model,
            input_tokens=int(input_tokens or 0),
            output_tokens=int(output_tokens or 0),
        )
    )
