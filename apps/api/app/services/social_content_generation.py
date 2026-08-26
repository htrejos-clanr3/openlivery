"""Structured social caption / carousel generation using agency AI credentials."""

from __future__ import annotations

import json
import re

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Client
from .providers import resolve_provider_credentials


def _brand_context(client: Client) -> str:
    return (
        f"Client: {client.name}\n"
        f"Industry: {client.industry}\n"
        f"Description: {client.description}\n"
        f"Context: {client.general_context}\n"
        f"Brand voice: {client.brand_voice or 'professional and clear'}\n"
    )


def _extract_json(text: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", text)
    raw = match.group(0) if match else text
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="AI returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="AI returned unexpected shape")
    return data


async def generate_social_content(
    db: Session,
    *,
    client: Client,
    content_type: str,
    objective: str,
    audience: str = "",
    user_instruction: str = "",
    slide_count: int = 5,
    language: str = "es",
) -> dict:
    """Return structured editable content. Never publishes."""
    brand = _brand_context(client)
    instruction = user_instruction or objective
    prompt = f"""You are the content assistant for {client.name}.

Brand:
{brand}

Objective:
{objective}

Audience:
{audience or 'general customers'}

Content type:
{content_type}

Instruction:
{instruction}

Language: {language}

Rules:
- Do NOT invent prices, statistics, phone numbers, URLs, certifications, or promotions.
- Use only facts implied by the brand context.
- Return ONLY valid JSON.

For IMAGE or REEL return:
{{
  "title": "...",
  "caption": "...",
  "cta": "...",
  "hashtags": ["#tag1", "#tag2"],
  "visualSuggestion": "...",
  "imagePrompt": "..."
}}

For CAROUSEL return:
{{
  "title": "...",
  "caption": "...",
  "cta": "...",
  "hashtags": ["#tag1"],
  "slides": [
    {{"order": 1, "headline": "...", "body": "...", "visualSuggestion": "..."}}
  ]
}}
Use exactly {slide_count} slides for CAROUSEL.
"""

    creds = resolve_provider_credentials(db, client.agency_id, "openai")
    if not creds:
        # Deterministic fallback without LLM (keeps UI usable).
        if content_type == "CAROUSEL":
            slides = [
                {
                    "order": i + 1,
                    "headline": f"{i + 1}. {objective[:80] or 'Idea'}",
                    "body": instruction[:280] or objective[:280] or "Edit this slide.",
                    "visualSuggestion": "Clean branded illustration matching brand colors.",
                }
                for i in range(max(2, min(slide_count, 10)))
            ]
            return {
                "title": objective[:120] or "Carousel",
                "caption": objective or instruction,
                "cta": "",
                "hashtags": [],
                "slides": slides,
            }
        return {
            "title": objective[:120] or "Post",
            "caption": instruction or objective,
            "cta": "",
            "hashtags": [],
            "visualSuggestion": "Product or service visual aligned with brand voice.",
            "imagePrompt": f"Brand visual for: {objective}",
        }

    base_url, api_key = creds
    model = "gpt-4.1-mini"
    async with httpx.AsyncClient(timeout=90) as http:
        response = await http.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "temperature": 0.7,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": "You generate structured social media copy as JSON only."},
                    {"role": "user", "content": prompt},
                ],
            },
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"AI provider error: {response.text[:300]}")
    payload = response.json()
    text = (((payload.get("choices") or [{}])[0].get("message") or {}).get("content")) or "{}"
    data = _extract_json(text)
    hashtags = data.get("hashtags") or []
    if isinstance(hashtags, str):
        hashtags = [h for h in hashtags.split() if h.startswith("#")]
    data["hashtags"] = [str(h) for h in hashtags if str(h).startswith("#")][:20]
    if content_type == "CAROUSEL":
        slides = data.get("slides") or []
        normalized = []
        for i, slide in enumerate(slides[:10]):
            if not isinstance(slide, dict):
                continue
            normalized.append(
                {
                    "order": int(slide.get("order") or i + 1),
                    "headline": str(slide.get("headline") or "")[:240],
                    "body": str(slide.get("body") or "")[:2000],
                    "visualSuggestion": str(slide.get("visualSuggestion") or slide.get("imagePrompt") or "")[:500],
                }
            )
        while len(normalized) < max(2, min(slide_count, 10)):
            n = len(normalized) + 1
            normalized.append(
                {"order": n, "headline": f"Slide {n}", "body": "", "visualSuggestion": ""}
            )
        data["slides"] = normalized
    data.setdefault("caption", "")
    data.setdefault("cta", "")
    data.setdefault("title", "")
    return data


class MediaGenerationProvider:
    """Future hook for image generation. Not used in MVP."""

    async def generate(self, *_args, **_kwargs) -> None:
        raise NotImplementedError("Image generation is not enabled in the MVP")
