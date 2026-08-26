"""Generate Instagram carousel drafts from client brand DNA + brief."""

from __future__ import annotations

import json
import re

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Carousel, CarouselEvent, CarouselSlide, Client, User, now_utc
from .providers import resolve_provider_credentials


def _event(db: Session, carousel: Carousel, *, actor_type: str, actor_id, action: str, payload: dict | None = None) -> None:
    db.add(
        CarouselEvent(
            carousel_id=carousel.id,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            payload=payload or {},
        )
    )


def _brand_context(client: Client) -> str:
    return (
        f"Cliente: {client.name}\n"
        f"Industria: {client.industry}\n"
        f"Contexto: {client.general_context or client.description}\n"
        f"Voz de marca: {client.brand_voice or 'profesional y clara'}\n"
        f"Color primario: {client.brand_primary_color}\n"
        f"Color secundario: {client.brand_secondary_color}\n"
        f"Fuente: {client.brand_font or 'sans-serif'}\n"
    )


def _parse_slides_json(text: str, slide_count: int) -> tuple[list[dict[str, str]], str]:
    match = re.search(r"\{[\s\S]*\}|\[[\s\S]*\]", text)
    raw = match.group(0) if match else text
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = None
    slides: list[dict[str, str]] = []
    caption = ""
    if isinstance(data, dict) and isinstance(data.get("slides"), list):
        items = data["slides"]
        caption = str(data.get("caption") or "")
    elif isinstance(data, list):
        items = data
    else:
        items = []
    for i, item in enumerate(items[:slide_count]):
        if not isinstance(item, dict):
            continue
        slides.append(
            {
                "headline": str(item.get("headline") or item.get("title") or f"Slide {i + 1}")[:240],
                "body": str(item.get("body") or item.get("text") or "")[:2000],
                "cta": str(item.get("cta") or "")[:180],
            }
        )
    while len(slides) < slide_count:
        n = len(slides) + 1
        slides.append({"headline": f"Punto {n}", "body": "Completa este slide con tu mensaje.", "cta": ""})
    return slides, caption


def _fallback_slides(brief: str, slide_count: int, language: str) -> tuple[list[dict[str, str]], str]:
    hook = "Hook" if language.startswith("en") else "Gancho"
    cta = "Comment below" if language.startswith("en") else "Comenta abajo"
    slides = [{"headline": f"{hook}: {brief[:80]}", "body": brief[:400] or "Tu mensaje principal", "cta": ""}]
    for i in range(2, slide_count):
        slides.append(
            {
                "headline": f"{i}. Idea clave",
                "body": f"Desarrolla el punto {i} del brief.",
                "cta": "",
            }
        )
    slides.append({"headline": cta, "body": brief[:200] or "CTA final", "cta": cta})
    caption = brief[:500] if brief else ("New carousel" if language.startswith("en") else "Nuevo carrusel")
    return slides, caption


def _openai_chat_json(api_key: str, system: str, user: str) -> str:
    with httpx.Client(timeout=90.0) as client:
        resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4.1-mini",
                "temperature": 0.7,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=400, detail=f"Provider error: {resp.text[:300]}")
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _openai_image(api_key: str, prompt: str) -> tuple[bytes, str] | None:
    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-image-1",
                    "prompt": prompt,
                    "size": "1024x1536",
                    "n": 1,
                },
            )
        if resp.status_code >= 400:
            return None
        data = resp.json()
        b64 = data["data"][0].get("b64_json")
        if not b64:
            return None
        import base64

        return base64.b64decode(b64), "image/png"
    except Exception:  # noqa: BLE001
        return None


def generate_carousel_content(
    db: Session,
    carousel: Carousel,
    client: Client,
    user: User,
    *,
    regenerate: bool = False,
    with_images: bool = True,
) -> Carousel:
    language = carousel.language or "es"
    slide_count = max(3, min(carousel.slide_count or 8, 12))
    system = (
        "You create Instagram carousel drafts. Reply ONLY with JSON: "
        '{"caption":"...","slides":[{"headline":"...","body":"...","cta":"..."}]} . '
        f"Language: {language}. Exactly {slide_count} slides. "
        "Slide 1 is a hook; last slide is a CTA. Keep headlines short."
    )
    user_prompt = f"{_brand_context(client)}\nBrief:\n{carousel.brief or carousel.title}\n"
    slides_data: list[dict[str, str]]
    caption = carousel.caption
    api_key = None
    try:
        creds = resolve_provider_credentials(db, user.agency_id, "openai")
        api_key = creds[1] if creds else None
    except Exception:  # noqa: BLE001
        api_key = None

    if api_key:
        try:
            raw = _openai_chat_json(api_key, system, user_prompt)
            slides_data, new_caption = _parse_slides_json(raw, slide_count)
            if new_caption:
                caption = new_caption
        except HTTPException:
            slides_data, caption = _fallback_slides(carousel.brief, slide_count, language)
    else:
        slides_data, caption = _fallback_slides(carousel.brief, slide_count, language)

    if regenerate or carousel.slides:
        for slide in list(carousel.slides):
            db.delete(slide)
        db.flush()

    primary = client.brand_primary_color or "#075985"
    secondary = client.brand_secondary_color or "#0f172a"
    for i, item in enumerate(slides_data):
        layout = {
            "format": "1080x1350",
            "primary": primary,
            "secondary": secondary,
            "font": client.brand_font or "Inter",
            "voice": client.brand_voice or "",
        }
        image_data = None
        image_mime = None
        if with_images and api_key:
            img_prompt = (
                f"Instagram carousel slide, vertical 4:5, brand colors {primary} and {secondary}, "
                f"minimal text space for headline '{item['headline']}', on-brand, no watermarks"
            )
            generated = _openai_image(api_key, img_prompt)
            if generated:
                image_data, image_mime = generated
        slide = CarouselSlide(
            carousel_id=carousel.id,
            position=i + 1,
            headline=item["headline"],
            body=item["body"],
            cta=item.get("cta") or "",
            layout_json=layout,
            image_data=image_data,
            image_mime=image_mime,
            agency_status="pending",
            client_status="pending",
        )
        db.add(slide)

    carousel.caption = caption
    carousel.slide_count = len(slides_data)
    carousel.status = "draft"
    carousel.updated_at = now_utc()
    _event(db, carousel, actor_type="agency", actor_id=user.id, action="generate", payload={"slides": len(slides_data)})
    db.commit()
    db.refresh(carousel)
    return carousel
