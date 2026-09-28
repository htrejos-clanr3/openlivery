"""Decide whether a contact event is a commercial opportunity.

This is a seam for later model-backed intent detection (OpenAI, DeepSeek, Qwen).
The default rule does not call any LLM.
"""

from __future__ import annotations

from dataclasses import dataclass


COMMERCIAL_SOURCES = frozenset({"form", "webhook", "instagram", "facebook", "whatsapp", "widget"})


@dataclass(frozen=True)
class DetectionResult:
    should_create_lead: bool
    reason: str
    score: int | None = None
    provider: str = "rule"


class LeadDetectionService:
    """Simple commercial-intent gate. Swap or subclass to plug in an LLM later."""

    def detect(
        self,
        *,
        source: str,
        enabled_sources: set[str],
        text: str | None = None,
    ) -> DetectionResult:
        source = (source or "").strip()
        if source not in enabled_sources:
            return DetectionResult(False, "source_disabled")
        if source not in COMMERCIAL_SOURCES:
            return DetectionResult(False, "unknown_source")
        # Form/webhook submissions are explicit opportunities.
        if source in {"form", "webhook"}:
            return DetectionResult(True, "inbound_form")
        # Chat channels: treat a new contact on an enabled source as commercial.
        # Future: inspect ``text`` with a model and return score.
        _ = text
        return DetectionResult(True, "new_contact_on_channel")


detection_service = LeadDetectionService()
