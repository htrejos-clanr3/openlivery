"""Generate Instagram carousel drafts from client brand DNA + brief."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Agent, Carousel, CarouselEvent, CarouselSlide, Client, User, now_utc
from .image_generation import backend_label, generate_slide_image, resolve_image_backend
from .slide_branding import apply_brand_mark
from .knowledge import retrieve_knowledge
from .providers import PROVIDERS, resolve_provider_credentials
from .format_playbook import assign_slide_cta, playbook_prompt, slide_role_hint
from .usage import persist_usage_rows, usage_entry


logger = logging.getLogger(__name__)

IMAGE_SCENE_SPEC = (
    "image_scene: 40–90 words in ENGLISH describing the visual for THAT slide. "
    "First choose the medium from the PRODUCT or SERVICE (never default to people or photorealism): "
    "environment/set, object or still-life, people only if the offer is human/service-in-person, "
    "documentary photo, 3D, animation still, cartoon, illustration, or mixed. "
    "Food → plated product or kitchen; kids brand → cartoon; luxury object → still-life; "
    "software → the system in the real workplace OR symbolic objects of that job, not generic office portraits. "
    "No letters, numbers, headlines, slogans, CTAs, logos, watermarks, or fake phone UI. "
    "Do not describe a logo; the real brand mark is composited later. "
    "Each slide a different visual. Vertical 4:5."
)
SLIDE_JSON_SHAPE = (
    '{"caption":"...","slides":[{"headline":"...","body":"...","cta":"...","image_scene":"..."}]}'
)
ONE_SLIDE_JSON_SHAPE = '{"headline":"...","body":"...","cta":"...","image_scene":"..."}'
CHAT_PROVIDER_ORDER = ("moonshot", "deepseek", "openai", "dashscope")
CHAT_MODELS = {
    "moonshot": "kimi-k2.5",
    "deepseek": "deepseek-chat",
    "openai": "gpt-4.1-mini",
    "dashscope": "qwen-plus",
}


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
        f"Descripción: {client.description or ''}\n"
        f"Contexto general: {client.general_context or ''}\n"
        f"Voz de marca: {client.brand_voice or 'profesional y clara'}\n"
        f"Color primario: {client.brand_primary_color}\n"
        f"Color secundario: {client.brand_secondary_color}\n"
        f"Fuente: {client.brand_font or 'sans-serif'}\n"
    )


def _agent_brief_block(agent: Agent) -> str:
    fields = (
        ("Qué hace el negocio", agent.brief_summary),
        ("Productos y servicios", agent.brief_products),
        ("Público objetivo", agent.brief_audience),
        ("Información y políticas", agent.brief_policies),
        ("Objetivo del agente", agent.brief_goal),
        ("Debe hacer", agent.brief_dos),
        ("No debe hacer", agent.brief_donts),
        ("Descripción", agent.description),
        ("Personalidad", agent.personality),
        ("Contexto manual", agent.manual_context),
        ("Instrucciones", agent.instructions),
    )
    lines = [f"- {label}: {value.strip()}" for label, value in fields if (value or "").strip()]
    if not lines:
        return ""
    return f"Agente «{agent.name}»:\n" + "\n".join(lines)


def _run_async(coro):
    """Run async helpers from sync FastAPI route handlers (threadpool-safe)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # Already inside a loop (rare for sync routes): fall back without RAG embeddings.
    return None


def gather_company_context(db: Session, client: Client, query: str) -> str:
    """Company DNA for interpret mode: client + agent briefs + RAG/embeddings knowledge."""
    parts = [_brand_context(client)]
    agents = list(
        db.scalars(
            select(Agent)
            .options(selectinload(Agent.qa_pairs), selectinload(Agent.documents))
            .where(Agent.client_id == client.id, Agent.is_active.is_(True))
            .order_by(Agent.created_at.asc())
        ).all()
    )
    for agent in agents[:4]:
        brief = _agent_brief_block(agent)
        if brief:
            parts.append(brief)
        qa = list(agent.qa_pairs or [])[:8]
        if qa:
            qa_lines = "\n".join(f"Q: {row.question}\nA: {row.answer}" for row in qa if row.question)
            if qa_lines.strip():
                parts.append(f"FAQ «{agent.name}»:\n{qa_lines}")

    rag_query = (query or client.name or "empresa").strip()[:500]
    for agent in agents[:2]:
        try:
            result = _run_async(retrieve_knowledge(db, agent, rag_query))
            if result and (result.text or "").strip():
                parts.append(f"Knowledge RAG («{agent.name}», embeddings):\n{result.text.strip()[:6000]}")
                break
        except Exception:  # noqa: BLE001
            continue

    return "\n\n".join(p for p in parts if p.strip())


def _slide_fields(item: dict, *, index: int = 1) -> dict[str, str]:
    return {
        "headline": str(item.get("headline") or item.get("title") or f"Slide {index}")[:240],
        "body": str(item.get("body") or item.get("text") or "")[:2000],
        "cta": str(item.get("cta") or "")[:180],
        "image_scene": str(
            item.get("image_scene") or item.get("image_prompt") or item.get("visual") or ""
        ).strip()[:800],
    }


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
        slides.append(_slide_fields(item, index=i + 1))
    while len(slides) < slide_count:
        n = len(slides) + 1
        slides.append({"headline": f"Punto {n}", "body": "Completa este slide con tu mensaje.", "cta": ""})
    return slides, caption


def _parse_single_slide_json(text: str) -> dict[str, str]:
    match = re.search(r"\{[\s\S]*\}", text)
    raw = match.group(0) if match else text
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Could not parse slide JSON from provider") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Provider returned invalid slide JSON")
    return _slide_fields(data)


def _parse_scenes_json(text: str, count: int) -> dict[int, str]:
    match = re.search(r"\{[\s\S]*\}", text)
    raw = match.group(0) if match else text
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    items = []
    if isinstance(data, dict):
        items = data.get("scenes") or data.get("slides") or []
        if isinstance(data.get("image_scene"), str) and count == 1:
            return {1: data["image_scene"].strip()[:800]}
    elif isinstance(data, list):
        items = data
    out: dict[int, str] = {}
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        idx = int(item.get("i") or item.get("index") or (i + 1))
        scene = str(item.get("image_scene") or item.get("visual") or "").strip()[:800]
        if scene:
            out[idx] = scene
    return {k: v for k, v in out.items() if 1 <= k <= count}


def _ensure_image_scenes(
    slides: list[dict[str, str]],
    *,
    base_url: str,
    api_key: str,
    model: str,
    company: str,
) -> tuple[list[dict[str, str]], dict | None]:
    if all((item.get("image_scene") or "").strip() for item in slides):
        return slides, None
    payload = [
        {"i": i + 1, "headline": item.get("headline") or "", "body": (item.get("body") or "")[:240]}
        for i, item in enumerate(slides)
    ]
    system = (
        "You assign a visual to each Instagram carousel slide from the product/service, not from a people-photo default. "
        'Reply ONLY with JSON: {"scenes":[{"i":1,"image_scene":"..."}]}. '
        f"{IMAGE_SCENE_SPEC}"
    )
    user = f"{company}\n\nSlides:\n{json.dumps(payload, ensure_ascii=False)}"
    raw, usage = _openai_chat_json(
        base_url=base_url, api_key=api_key, model=model, system=system, user=user
    )
    scenes = _parse_scenes_json(raw, len(slides))
    for i, item in enumerate(slides):
        if not (item.get("image_scene") or "").strip() and scenes.get(i + 1):
            item["image_scene"] = scenes[i + 1]
    return slides, usage


def _chat_one_image_scene(
    *,
    base_url: str,
    api_key: str,
    model: str,
    company: str,
    headline: str,
    body: str,
) -> tuple[str, dict]:
    system = (
        "You pick one visual for an Instagram slide from the product/service. "
        f'Reply ONLY with JSON: {{"image_scene":"..."}}. {IMAGE_SCENE_SPEC}'
    )
    user = (
        f"{company}\n\n"
        f"Slide headline (do not paint as text): {headline}\n"
        f"Slide message (do not paint as text): {body}\n"
        "Write image_scene."
    )
    raw, usage = _openai_chat_json(
        base_url=base_url, api_key=api_key, model=model, system=system, user=user
    )
    scenes = _parse_scenes_json(raw, 1)
    scene = scenes.get(1) or ""
    if not scene:
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                scene = str(data.get("image_scene") or "")[:800]
        except json.JSONDecodeError:
            scene = ""
    return scene.strip(), usage


def _fallback_slides(
    brief: str,
    slide_count: int,
    language: str,
    *,
    title: str = "",
    cta_instruction: str = "",
    hook_structure: bool = True,
) -> tuple[list[dict[str, str]], str]:
    idea = (brief or title or "").strip()
    es = not language.startswith("en")
    hook = "Gancho" if es else "Hook"
    enganche = "Enganche" if es else "Stay with this"
    cta = (cta_instruction or "").strip()[:180] or ("Escríbenos hoy" if es else "Message us today")
    parts = [p.strip() for p in re.split(r"[.\n;•]+", idea) if p.strip()]
    while len(parts) < max(1, slide_count - 2):
        parts.append(idea or ("Beneficio clave" if es else "Key benefit"))
    slides = [
        {
            "headline": f"{hook}: {(parts[0][:70] if parts else idea)[:70]}",
            "body": (parts[0] if parts else idea)[:280]
            or ("Tu mensaje principal, en una frase clara." if es else "Your main message in one clear line."),
            "cta": "",
        }
    ]
    for i in range(1, slide_count - 1):
        chunk = parts[min(i, len(parts) - 1)]
        is_enganche = hook_structure and i == 1
        slides.append(
            {
                "headline": (
                    f"{enganche}: {chunk[:50]}" if is_enganche and chunk else (chunk[:60] if chunk else (f"Punto {i + 1}" if es else f"Point {i + 1}"))
                ),
                "body": (chunk[:320] if chunk else idea[:320])
                or (f"Desarrolla el beneficio {i + 1}." if es else f"Expand benefit {i + 1}."),
                "cta": "",
            }
        )
    slides.append(
        {
            "headline": cta,
            "body": (idea[:200] if idea else ("Da el siguiente paso con nosotros." if es else "Take the next step with us.")),
            "cta": cta,
        }
    )
    caption = idea[:500] if idea else ("Nuevo carrusel" if es else "New carousel")
    return slides[:slide_count], caption


def resolve_chat_credentials(db: Session, agency_id) -> tuple[str, str, str] | None:
    """(provider, base_url, api_key) for carousel copy generation."""
    for provider in CHAT_PROVIDER_ORDER:
        if provider not in PROVIDERS:
            continue
        try:
            creds = resolve_provider_credentials(db, agency_id, provider)
        except Exception:  # noqa: BLE001
            continue
        if creds:
            return provider, creds[0], creds[1]
    return None


def resolve_image_credentials(db: Session, agency_id) -> tuple[str, str] | None:
    """(base_url, api_key) for OpenAI Images. Prefer resolve_image_backend()."""
    backend = resolve_image_backend(db, agency_id)
    if not backend or backend.provider != "openai":
        return None
    return backend.base_url, backend.api_key


def _openai_chat_json(
    *,
    base_url: str,
    api_key: str,
    model: str,
    system: str,
    user: str,
) -> tuple[str, dict]:
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload: dict = {
        "model": model,
        "temperature": 0.7,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    # OpenAI / DeepSeek support json_object; Moonshot may ignore unknown fields.
    if "openai.com" in base_url or "deepseek" in base_url:
        payload["response_format"] = {"type": "json_object"}
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=400, detail=f"Provider error ({model}): {resp.text[:300]}")
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return content, _parse_token_usage(data)


def _parse_token_usage(data: dict) -> dict:
    usage = data.get("usage") or {}
    return {
        "input_tokens": int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or usage.get("completion_tokens") or 0),
    }


def _generate_one_slide_image(
    *,
    backend,
    item: dict[str, str],
    primary: str,
    secondary: str,
    description: str,
    related_only: bool,
    custom_prompt: str | None = None,
    company: str = "",
    product_image: bytes | None = None,
    product_mime: str | None = None,
    brand_logo: bytes | None = None,
    brand_logo_mime: str | None = None,
    brand_name: str = "",
) -> tuple[bytes | None, str | None, str | None, str, dict]:
    """Return (bytes, mime, error, prompt_used, usage)."""
    prompt = (custom_prompt or "").strip()
    if not prompt or _is_legacy_generic_style_prompt(prompt):
        prompt = _slide_image_prompt(
            item=item,
            primary=primary,
            secondary=secondary,
            description=description,
            related_only=related_only,
            company=company,
            has_product=bool(product_image),
        )
    prompt = prompt[:3500]
    if product_image and "product photo" not in prompt.lower() and "foto de producto" not in prompt.lower():
        prompt = (
            prompt
            + " A real product photo is attached. Isolate the product (remove the original background), "
            "clean it, and restage it as the hero of this advertisement matching the slide message."
        )[:3500]
    data, mime, err, usage = generate_slide_image(
        backend,
        prompt,
        product_image=product_image,
        product_mime=product_mime,
    )
    if data:
        try:
            data, mime = apply_brand_mark(
                data,
                logo_bytes=brand_logo,
                logo_mime=brand_logo_mime,
                brand_name=brand_name,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("brand mark composite failed: %s", exc)
    return data, mime, err, prompt, usage


def _is_legacy_generic_style_prompt(prompt: str) -> bool:
    """Old auto prompts forced glass cubes on every slide; rebuild those."""
    lowered = (prompt or "").lower()
    return (
        "frosted cubes" in lowered
        or "glassmorphism 3d" in lowered
        or "headline:" in lowered
        or "illustrate this slide" in lowered
        or "message:" in lowered
        or "photorealistic vertical 4:5 photograph" in lowered
        or "photograph a concrete real-world scene" in lowered
    )


def _slide_image_prompt(
    *,
    item: dict[str, str],
    primary: str,
    secondary: str,
    description: str,
    related_only: bool = False,
    company: str = "",
    has_product: bool = False,
) -> str:
    scene = (item.get("image_scene") or "").strip()[:800]
    desc = (description or "").strip()[:400]
    company_snip = (company or "").strip()[:700]
    style = (
        "Vertical 4:5 Instagram carousel visual. "
        "Pick the medium from the product or service — environment, objects/still-life, people, "
        "photo, 3D, animation still, cartoon, or illustration. "
        "Do not default to people or photorealism if another medium fits the offer better. "
        "Only the picture — no headline, no caption, no CTA, no slogan, no watermark, no fake phone UI. "
        "Zero text in the pixels: no letters, numbers, posters, signs, or invented logos "
        "(the real brand mark is added later). "
        "Forbidden: generic glass cubes, neon grids, empty gradients unrelated to the offer. "
        f"Brand accents {primary} and {secondary} as small highlights only."
    )
    if related_only:
        meaning = (
            "One visual of this product or service. Choose medium from the offer "
            f"(not automatically people): {desc or company_snip or 'the offer'}."
        )
    elif scene:
        meaning = f"Visual (chosen from the product/service):\n{scene}"
    else:
        meaning = (
            "Invent one visual that expresses this product or service. "
            "Choose the medium that fits (objects, place, people, cartoon, animation, photo, etc.). "
            f"Offer/context: {company_snip or desc or 'the offer'}."
        )
    product = ""
    if has_product:
        product = (
            " A real product photo is attached. Isolate the product (remove the original background), "
            "clean, color-correct and sharpen it, then composite it as the hero of this visual. "
            "Keep the product recognizable. Still no text or invented logos."
        )
    return f"{style}\n{meaning}{product}"


def generate_carousel_content(
    db: Session,
    carousel: Carousel,
    client: Client,
    user: User,
    *,
    regenerate: bool = False,
    with_images: bool = True,
    interpret_prompt: bool | None = None,
    ensure_min_image: bool = True,
    include_approved: bool = False,
) -> Carousel:
    carousel.generating_at = now_utc()
    db.add(carousel)
    db.commit()
    notes: list[str] = []
    result: Carousel | None = None
    try:
        result = _generate_carousel_content_impl(
            db,
            carousel,
            client,
            user,
            regenerate=regenerate,
            with_images=with_images,
            interpret_prompt=interpret_prompt,
            ensure_min_image=ensure_min_image,
            include_approved=include_approved,
            notes=notes,
        )
    finally:
        carousel.generating_at = None
        carousel.updated_at = now_utc()
        db.add(carousel)
        db.commit()
        db.refresh(carousel)
        setattr(carousel, "_generation_notes", notes)
        usage = getattr(result, "_generation_usage", None) if result is not None else None
        if usage:
            setattr(carousel, "_generation_usage", usage)
    assert result is not None
    return result


def _approved_continuity_prompt(slides: list[CarouselSlide], replace_positions: list[int]) -> str:
    kept = "\n".join(
        f"#{s.position} HEADLINE: {s.headline} | BODY: {s.body} | CTA: {s.cta or '—'}"
        for s in sorted(slides, key=lambda row: row.position)
    )
    positions = ", ".join(str(p) for p in replace_positions)
    return (
        "Approved slides that MUST stay unchanged (do not rewrite or duplicate them):\n"
        f"{kept}\n"
        f"Generate ONLY {len(replace_positions)} new slides for positions {positions}, in that order. "
        "They must fit the same carousel story."
    )


def _generate_carousel_content_impl(
    db: Session,
    carousel: Carousel,
    client: Client,
    user: User,
    *,
    regenerate: bool,
    with_images: bool,
    interpret_prompt: bool | None,
    ensure_min_image: bool,
    include_approved: bool,
    notes: list[str],
) -> Carousel:
    language = carousel.language or "es"
    full_count = max(3, min(carousel.slide_count or 7, 12))
    interpret = carousel.interpret_prompt if interpret_prompt is None else interpret_prompt
    carousel.interpret_prompt = bool(interpret)
    hook_structure = bool(getattr(carousel, "hook_structure", True))
    content_goal = getattr(carousel, "content_goal", None) or "loyalty"
    cta_instruction = (getattr(carousel, "cta_instruction", None) or "").strip()
    playbook = playbook_prompt(
        content_type="CAROUSEL",
        content_goal=content_goal,
        cta_instruction=cta_instruction,
        hook_structure=hook_structure,
        slide_count=full_count,
    )

    idea = (carousel.title or "").strip()
    brief = (carousel.brief or "").strip() or idea
    company = gather_company_context(db, client, f"{idea}\n{brief}") if interpret else _brand_context(client)

    existing_slides = list(carousel.slides)
    keep_approved = bool(regenerate and existing_slides and not include_approved)
    kept_slides = [s for s in existing_slides if s.agency_status == "agency_ok"] if keep_approved else []
    kept_positions = {s.position for s in kept_slides}
    target_count = max(full_count, max((s.position for s in kept_slides), default=0))
    replace_positions = [p for p in range(1, target_count + 1) if p not in kept_positions]
    generate_count = len(replace_positions) if keep_approved else full_count

    if keep_approved and not replace_positions:
        notes.append("All slides are already approved; none were regenerated.")
        return carousel

    continuity = _approved_continuity_prompt(kept_slides, replace_positions) if keep_approved else ""
    count_rule = (
        f"Language: {language}. Exactly {generate_count} slides"
        + (f" for positions {', '.join(str(p) for p in replace_positions)}" if keep_approved else "")
        + "."
    )

    if interpret:
        system = (
            "You are a senior social creative. The title/brief is an INTENT, not final copy. "
            "Interpret it using the company knowledge (products, features, RAG excerpts) and build a full Instagram carousel. "
            "Example intent: «Toma las principales funcionalidades de lo que hace la empresa» → extract real features from company context. "
            "Example intent: «Promoción del día» → invent a concrete promo grounded in products/services from context. "
            "Reply ONLY with JSON: "
            f"{SLIDE_JSON_SHAPE} . "
            f"{count_rule} "
            "Rules: (1) Do NOT paste the intent verbatim on every slide. "
            f"(2) {playbook} "
            "(3) Headlines ≤ 8 words. (4) caption with 3–6 hashtags. "
            f"(5) Every slide MUST include image_scene. {IMAGE_SCENE_SPEC}"
        )
        user_prompt = (
            f"{company}\n\n"
            f"Intent / title: {idea}\n"
            f"Intent / brief: {brief}\n"
            + (f"{continuity}\n" if continuity else "")
            + "Interpret the intent with the company knowledge above and generate the carousel."
        )
    else:
        system = (
            "You format an Instagram carousel using the EXACT title and brief provided. "
            "Do not invent products or features beyond what the user wrote. "
            "You may split/shorten for slide fit, but keep the wording faithful. "
            "Reply ONLY with JSON: "
            f"{SLIDE_JSON_SHAPE} . "
            f"{count_rule} "
            f"{playbook} "
            "Slide 1 uses the title/hook; last slide may add a short CTA if missing. "
            f"Every slide MUST include image_scene. {IMAGE_SCENE_SPEC}"
        )
        user_prompt = (
            f"{_brand_context(client)}\n"
            f"EXACT title: {idea}\n"
            f"EXACT brief/body: {brief}\n"
            + (f"{continuity}\n" if continuity else "")
            + "Format into slides without changing meaning."
        )

    slides_data: list[dict[str, str]]
    caption = carousel.caption
    used_fallback = False

    usage_rows: list[dict] = []
    chat = resolve_chat_credentials(db, user.agency_id)
    image_backend = resolve_image_backend(db, user.agency_id)

    if chat:
        provider, base_url, chat_key = chat
        model = CHAT_MODELS.get(provider, "deepseek-chat")
        try:
            raw, chat_usage = _openai_chat_json(
                base_url=base_url,
                api_key=chat_key,
                model=model,
                system=system,
                user=user_prompt,
            )
            slides_data, new_caption = _parse_slides_json(raw, generate_count)
            if new_caption and not keep_approved:
                caption = new_caption
            notes.append(f"Copy generated with {PROVIDERS[provider]['label']} ({model}).")
            usage_rows.append(
                usage_entry(
                    kind="copy",
                    provider=provider,
                    model=model,
                    input_tokens=chat_usage.get("input_tokens", 0),
                    output_tokens=chat_usage.get("output_tokens", 0),
                    label="copy",
                )
            )
            try:
                slides_data, scene_usage = _ensure_image_scenes(
                    slides_data,
                    base_url=base_url,
                    api_key=chat_key,
                    model=model,
                    company=company,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("image_scene fill failed: %s", exc)
                scene_usage = None
            if scene_usage:
                usage_rows.append(
                    usage_entry(
                        kind="copy",
                        provider=provider,
                        model=model,
                        input_tokens=scene_usage.get("input_tokens", 0),
                        output_tokens=scene_usage.get("output_tokens", 0),
                        label="image scenes",
                    )
                )
                notes.append("Slide visuals chosen from product/service (not a people-photo default).")
        except HTTPException as exc:
            slides_data, new_caption = _fallback_slides(
                brief, generate_count, language, title=idea, cta_instruction=cta_instruction, hook_structure=hook_structure
            )
            if not keep_approved:
                caption = new_caption
            used_fallback = True
            notes.append(f"Chat provider failed ({exc.detail}); used template fallback.")
    else:
        slides_data, new_caption = _fallback_slides(
            brief, generate_count, language, title=idea, cta_instruction=cta_instruction, hook_structure=hook_structure
        )
        if not keep_approved:
            caption = new_caption
        used_fallback = True
        notes.append(
            "No chat provider key found. Configure Kimi (Moonshot), DeepSeek, or OpenAI in Settings → Providers. "
            "Used template fallback (looks unchanged)."
        )

    if keep_approved:
        slides_data = slides_data[: len(replace_positions)]
        while len(slides_data) < len(replace_positions):
            n = len(slides_data) + 1
            slides_data.append({"headline": f"Punto {n}", "body": "Completa este slide con tu mensaje.", "cta": ""})
        position_items = list(zip(replace_positions, slides_data))
    else:
        position_items = [(i + 1, item) for i, item in enumerate(slides_data)]

    position_items = [
        (
            pos,
            assign_slide_cta(
                dict(item),
                position=pos,
                total=target_count,
                cta_instruction=cta_instruction,
            ),
        )
        for pos, item in position_items
    ]

    if regenerate or existing_slides:
        kept_products: dict[int, tuple[bytes, str]] = {}
        for slide in existing_slides:
            if keep_approved and slide.agency_status == "agency_ok":
                continue
            if slide.product_image_data and slide.product_image_mime:
                kept_products[slide.position] = (slide.product_image_data, slide.product_image_mime)
            db.delete(slide)
        db.flush()
    else:
        kept_products = {}

    primary = client.brand_primary_color or "#075985"
    secondary = client.brand_secondary_color or "#0f172a"
    description_for_image = brief or idea or client.description or client.name
    company_for_image = (company if interpret else _brand_context(client))[:1600]
    kept_has_image = any(s.image_mime for s in kept_slides)
    want_images = with_images or (ensure_min_image and not kept_has_image)
    image_slots = 0
    skipped_product_edit = False
    if want_images and image_backend:
        image_slots = len(position_items) if with_images else 1
        image_slots = max(image_slots, 1 if (ensure_min_image and not kept_has_image) else 0)
    elif want_images and not image_backend:
        notes.append(
            "No image backend is ready. Set IMAGE_PROVIDER=huggingface with HF_TOKEN, "
            "IMAGE_PROVIDER=flux (local Flux Schnell sidecar), IMAGE_PROVIDER=placeholder "
            "(free test PNGs), or add an OpenAI key in Settings → Providers. "
            "Kimi/DeepSeek only generate text. Video is not used for Instagram carousels."
        )

    images_ok = 0
    image_errors: list[str] = []
    generated_by_position: dict[int, tuple[bytes | None, str | None, str | None, str, dict]] = {}

    if image_backend and image_slots > 0:
        jobs = []
        for job_i, (position, item) in enumerate(position_items):
            if job_i >= image_slots:
                break
            product = kept_products.get(position)
            jobs.append(
                (
                    position,
                    item,
                    not with_images and job_i == 0,
                    product[0] if product else None,
                    product[1] if product else None,
                )
            )
        workers = min(image_backend.max_workers, len(jobs))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    _generate_one_slide_image,
                    backend=image_backend,
                    item=item,
                    primary=primary,
                    secondary=secondary,
                    description=description_for_image,
                    related_only=related_only,
                    company=company_for_image,
                    product_image=product_bytes,
                    product_mime=product_mime,
                    brand_logo=client.brand_logo_data,
                    brand_logo_mime=client.brand_logo_mime,
                    brand_name=client.name,
                ): position
                for position, item, related_only, product_bytes, product_mime in jobs
            }
            for fut in as_completed(futures):
                position = futures[fut]
                try:
                    data, mime, err, prompt_used, img_usage = fut.result()
                except Exception as exc:  # noqa: BLE001
                    image_errors.append(f"slide {position}: {exc!s}"[:160])
                    continue
                generated_by_position[position] = (data, mime, err, prompt_used, img_usage)
                if img_usage.get("skipped_product_edit"):
                    skipped_product_edit = True
                if data:
                    usage_rows.append(
                        usage_entry(
                            kind="image",
                            provider=image_backend.provider,
                            model=img_usage.get("model") or image_backend.model,
                            input_tokens=img_usage.get("input_tokens", 0),
                            output_tokens=img_usage.get("output_tokens", 0),
                            label=f"slide {position}",
                        )
                    )
                elif err:
                    image_errors.append(f"slide {position}: {err}")
                    logger.warning("carousel_image_failed position=%s err=%s", position, err)

    for position, item in position_items:
        layout = {
            "format": "1080x1350",
            "primary": primary,
            "secondary": secondary,
            "font": client.brand_font or "Inter",
            "voice": client.brand_voice or "",
            "interpret_prompt": interpret,
        }
        image_data = None
        image_mime = None
        image_prompt = None
        image_error = None
        product = kept_products.get(position)
        if position in generated_by_position:
            image_data, image_mime, image_error, image_prompt, _img_usage = generated_by_position[position]
            if image_data:
                images_ok += 1
                image_error = None
        elif want_images:
            image_prompt = _slide_image_prompt(
                item=item,
                primary=primary,
                secondary=secondary,
                description=description_for_image,
                related_only=not with_images and position == position_items[0][0],
                company=company_for_image,
                has_product=bool(product),
            )
        slide = CarouselSlide(
            carousel_id=carousel.id,
            position=position,
            headline=item["headline"],
            body=item["body"],
            cta=item.get("cta") or "",
            layout_json=layout,
            image_data=image_data,
            image_mime=image_mime,
            image_prompt=image_prompt,
            image_error=image_error,
            product_image_data=product[0] if product else None,
            product_image_mime=product[1] if product else None,
            agency_status="pending",
            client_status="pending",
        )
        db.add(slide)

    if keep_approved:
        notes.append(f"Kept {len(kept_slides)} approved slide(s); regenerated {len(position_items)}.")

    if image_slots and images_ok == 0:
        tip = image_errors[0] if image_errors else f"Check image backend ({backend_label(image_backend) if image_backend else 'none'})."
        notes.append(f"No slide images generated. {tip}")
    elif images_ok:
        notes.append(f"Generated {images_ok}/{image_slots} slide image(s) with {backend_label(image_backend)}.")
        if skipped_product_edit:
            notes.append(
                "Product-photo restage (/images/edits) is OpenAI-only; local Flux/Ollama generated from the text prompt instead."
            )
        if image_errors:
            notes.append(f"{len(image_errors)} image(s) failed (first: {image_errors[0]})")

    carousel.caption = caption
    carousel.slide_count = target_count if keep_approved else len(slides_data)
    carousel.status = "draft"
    carousel.updated_at = now_utc()
    usage = persist_usage_rows(db, user.agency_id, usage_rows)
    if usage.get("items"):
        notes.append(
            f"Usage: {usage['input_tokens']} in / {usage['output_tokens']} out "
            f"(~${usage['estimated_usd']:.4f} list-price estimate)."
        )
    _event(
        db,
        carousel,
        actor_type="agency",
        actor_id=user.id,
        action="generate",
        payload={
            "slides": len(position_items),
            "kept_approved": len(kept_slides),
            "include_approved": include_approved,
            "interpret_prompt": interpret,
            "images": images_ok,
            "with_images": with_images,
            "used_fallback": used_fallback,
            "notes": notes,
            "image_errors": image_errors[:5],
            "usage": usage,
        },
    )
    db.commit()
    db.expire(carousel, ["slides"])
    db.refresh(carousel)
    setattr(carousel, "_generation_notes", notes)
    setattr(carousel, "_generation_usage", usage)
    return carousel


def regenerate_carousel_slide(
    db: Session,
    carousel: Carousel,
    slide: CarouselSlide,
    client: Client,
    user: User,
    *,
    with_images: bool = True,
    image_prompt: str | None = None,
    regenerate_copy: bool = True,
) -> Carousel:
    carousel.generating_at = now_utc()
    db.add(carousel)
    db.commit()
    notes: list[str] = []
    usage_rows: list[dict] = []
    result: Carousel | None = None
    try:
        result = _regenerate_carousel_slide_impl(
            db,
            carousel,
            slide,
            client,
            user,
            with_images=with_images,
            image_prompt=image_prompt,
            regenerate_copy=regenerate_copy,
            notes=notes,
            usage_rows=usage_rows,
        )
    finally:
        carousel.generating_at = None
        carousel.updated_at = now_utc()
        db.add(carousel)
        db.commit()
        db.refresh(carousel)
        setattr(carousel, "_generation_notes", notes)
        usage = getattr(result, "_generation_usage", None) if result is not None else None
        if usage:
            setattr(carousel, "_generation_usage", usage)
    assert result is not None
    return result


def _regenerate_carousel_slide_impl(
    db: Session,
    carousel: Carousel,
    slide: CarouselSlide,
    client: Client,
    user: User,
    *,
    with_images: bool,
    image_prompt: str | None,
    regenerate_copy: bool,
    notes: list[str],
    usage_rows: list[dict],
) -> Carousel:
    language = carousel.language or "es"
    interpret = bool(carousel.interpret_prompt)
    idea = (carousel.title or "").strip()
    brief = (carousel.brief or "").strip() or idea
    total = max(len(carousel.slides), carousel.slide_count or 1)
    position = slide.position
    company = gather_company_context(db, client, f"{idea}\n{brief}") if interpret else _brand_context(client)
    hook_structure = bool(getattr(carousel, "hook_structure", True))
    content_goal = getattr(carousel, "content_goal", None) or "loyalty"
    cta_instruction = (getattr(carousel, "cta_instruction", None) or "").strip()
    playbook = playbook_prompt(
        content_type="CAROUSEL",
        content_goal=content_goal,
        cta_instruction=cta_instruction,
        hook_structure=hook_structure,
        slide_count=total,
    )

    siblings = "\n".join(
        f"- Slide {s.position}: {s.headline} — {(s.body or '')[:120]}"
        for s in sorted(carousel.slides, key=lambda x: x.position)
        if s.id != slide.id
    )

    role_hint = slide_role_hint(
        position, total, hook_structure=hook_structure, cta_instruction=cta_instruction
    )

    slide_data: dict[str, str] = {
        "headline": slide.headline or "",
        "body": slide.body or "",
        "cta": slide.cta or "",
    }

    if regenerate_copy:
        if interpret:
            system = (
                "You rewrite ONE Instagram carousel slide. The carousel brief is an INTENT. "
                "Reply ONLY with JSON: "
                f"{ONE_SLIDE_JSON_SHAPE} . "
                f"Language: {language}. Headline ≤ 8 words. Do not copy other slides verbatim. "
                f"{playbook} "
                f"Include image_scene. {IMAGE_SCENE_SPEC}"
            )
            user_prompt = (
                f"{company}\n\n"
                f"Carousel title/intent: {idea}\nBrief: {brief}\n{role_hint}\n"
                f"Other slides in this carousel:\n{siblings or '(none)'}\n\n"
                f"Regenerate slide {position} with fresh copy aligned to the intent and company knowledge."
            )
        else:
            system = (
                "You rewrite ONE Instagram carousel slide using the exact carousel title/brief. "
                "Reply ONLY with JSON: "
                f"{ONE_SLIDE_JSON_SHAPE} . "
                f"Language: {language}. Keep meaning faithful; you may shorten for slide fit. "
                f"{playbook} "
                f"Include image_scene. {IMAGE_SCENE_SPEC}"
            )
            user_prompt = (
                f"{_brand_context(client)}\n"
                f"Title: {idea}\nBrief: {brief}\n{role_hint}\n"
                f"Other slides:\n{siblings or '(none)'}\n"
                f"Regenerate slide {position}."
            )

        chat = resolve_chat_credentials(db, user.agency_id)
        if chat:
            provider, base_url, chat_key = chat
            model = CHAT_MODELS.get(provider, "deepseek-chat")
            try:
                raw, chat_usage = _openai_chat_json(
                    base_url=base_url,
                    api_key=chat_key,
                    model=model,
                    system=system,
                    user=user_prompt,
                )
                slide_data = _parse_single_slide_json(raw)
                notes.append(f"Slide {position} copy regenerated with {provider} ({model}).")
                usage_rows.append(
                    usage_entry(
                        kind="copy",
                        provider=provider,
                        model=model,
                        input_tokens=chat_usage.get("input_tokens", 0),
                        output_tokens=chat_usage.get("output_tokens", 0),
                        label=f"slide {position}",
                    )
                )
            except HTTPException:
                raise
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(status_code=400, detail=f"Slide copy generation failed: {exc!s}") from exc
        else:
            fallback_slides, _ = _fallback_slides(
                brief, total, language, title=idea, cta_instruction=cta_instruction, hook_structure=hook_structure
            )
            slide_data = fallback_slides[min(position - 1, len(fallback_slides) - 1)]
            notes.append("No chat provider — used template fallback for this slide.")

        slide.headline = slide_data["headline"]
        slide.body = slide_data["body"]
        assign_slide_cta(
            slide_data,
            position=position,
            total=total,
            cta_instruction=cta_instruction,
        )
        slide.cta = slide_data.get("cta") or ""
        slide.agency_status = "pending"
        slide.client_status = "pending"
    else:
        notes.append(f"Slide {position}: kept existing copy; regenerating image only.")

    primary = client.brand_primary_color or "#075985"
    secondary = client.brand_secondary_color or "#0f172a"
    description_for_image = brief or idea or client.description or client.name
    layout = dict(slide.layout_json or {})
    layout.update(
        {
            "primary": primary,
            "secondary": secondary,
            "font": client.brand_font or layout.get("font") or "Inter",
            "interpret_prompt": interpret,
        }
    )
    slide.layout_json = layout

    custom = (image_prompt if image_prompt is not None else slide.image_prompt) or None
    custom = (custom or "").strip() or None
    company_for_image = gather_company_context(db, client, f"{idea}\n{brief}\n{slide_data.get('headline','')}\n{slide_data.get('body','')}") if interpret else _brand_context(client)

    if with_images and (not custom or _is_legacy_generic_style_prompt(custom)):
        chat = resolve_chat_credentials(db, user.agency_id)
        if chat and not (slide_data.get("image_scene") or "").strip():
            provider, base_url, chat_key = chat
            model = CHAT_MODELS.get(provider, "deepseek-chat")
            try:
                scene, scene_usage = _chat_one_image_scene(
                    base_url=base_url,
                    api_key=chat_key,
                    model=model,
                    company=company_for_image[:1600],
                    headline=slide_data.get("headline") or "",
                    body=slide_data.get("body") or "",
                )
                if scene:
                    slide_data["image_scene"] = scene
                    custom = None
                    usage_rows.append(
                        usage_entry(
                            kind="copy",
                            provider=provider,
                            model=model,
                            input_tokens=scene_usage.get("input_tokens", 0),
                            output_tokens=scene_usage.get("output_tokens", 0),
                            label=f"slide {position} scene",
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("single-slide image_scene failed: %s", exc)
        elif _is_legacy_generic_style_prompt(custom or ""):
            custom = None

    image_backend = resolve_image_backend(db, user.agency_id)
    if with_images and image_backend:
        data, mime, err, prompt_used, img_usage = _generate_one_slide_image(
            backend=image_backend,
            item=slide_data,
            primary=primary,
            secondary=secondary,
            description=description_for_image,
            related_only=False,
            custom_prompt=custom,
            company=company_for_image[:1600],
            product_image=slide.product_image_data,
            product_mime=slide.product_image_mime,
            brand_logo=client.brand_logo_data,
            brand_logo_mime=client.brand_logo_mime,
            brand_name=client.name,
        )
        slide.image_prompt = prompt_used
        if data:
            slide.image_data = data
            slide.image_mime = mime or "image/png"
            slide.image_error = None
            extra = " with product photo" if slide.product_image_data else ""
            notes.append(f"Slide {position} image regenerated with {backend_label(image_backend)}{extra}.")
            if img_usage.get("skipped_product_edit"):
                notes.append(
                    "Product-photo restage is OpenAI-only; this local backend generated from the text prompt."
                )
            usage_rows.append(
                usage_entry(
                    kind="image",
                    provider=image_backend.provider,
                    model=img_usage.get("model") or image_backend.model,
                    input_tokens=img_usage.get("input_tokens", 0),
                    output_tokens=img_usage.get("output_tokens", 0),
                    label=f"slide {position}",
                )
            )
        else:
            slide.image_error = err
            notes.append(f"Slide copy updated; image failed: {err}")
    elif with_images:
        slide.image_prompt = custom or _slide_image_prompt(
            item=slide_data,
            primary=primary,
            secondary=secondary,
            description=description_for_image,
            related_only=False,
            company=company_for_image[:1600],
            has_product=bool(slide.product_image_data),
        )
        notes.append(
            "No image backend is ready. Set IMAGE_PROVIDER=huggingface with HF_TOKEN, "
            "IMAGE_PROVIDER=flux, or add an OpenAI key. Text/prompt was updated."
        )
    elif custom is not None:
        slide.image_prompt = custom

    slide.updated_at = now_utc()
    carousel.updated_at = now_utc()
    usage = persist_usage_rows(db, user.agency_id, usage_rows)
    if usage.get("items"):
        notes.append(
            f"Usage: {usage['input_tokens']} in / {usage['output_tokens']} out "
            f"(~${usage['estimated_usd']:.4f} list-price estimate)."
        )
    _event(
        db,
        carousel,
        actor_type="agency",
        actor_id=user.id,
        action="regenerate_slide",
        payload={
            "slide_id": str(slide.id),
            "position": position,
            "with_images": with_images,
            "regenerate_copy": regenerate_copy,
            "custom_prompt": bool(custom),
            "notes": notes,
            "usage": usage,
        },
    )
    db.commit()
    db.refresh(carousel)
    setattr(carousel, "_generation_notes", notes)
    setattr(carousel, "_generation_usage", usage)
    return carousel
