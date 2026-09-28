from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..models import Carousel, CarouselEvent, CarouselSlide, Client, User, now_utc
from ..schemas import (
    CarouselCreate,
    CarouselGenerateRequest,
    CarouselOut,
    CarouselScheduleRequest,
    CarouselSlideDecision,
    CarouselSlideGenerateRequest,
    CarouselSlideOut,
    CarouselSlideUpdate,
    ImageCostQuoteOut,
)
from ..services.carousels import generate_carousel_content, regenerate_carousel_slide
from ..services.format_playbook import apply_playbook_to_carousel
from ..services.image_generation import quote_image_generation


router = APIRouter(prefix="/carousels", tags=["Carousels"])

GENERATION_STALE_SECONDS = 900
MAX_PRODUCT_BYTES = 8 * 1024 * 1024
ALLOWED_PRODUCT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}


def _client_for_agency(db: Session, user: User, client_id: uuid.UUID) -> Client:
    client = db.scalar(select(Client).where(Client.id == client_id, Client.agency_id == user.agency_id))
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def _carousel_for_agency(db: Session, user: User, carousel_id: uuid.UUID) -> Carousel:
    carousel = db.scalar(
        select(Carousel)
        .options(selectinload(Carousel.slides))
        .where(Carousel.id == carousel_id, Carousel.agency_id == user.agency_id)
    )
    if not carousel:
        raise HTTPException(status_code=404, detail="Carousel not found")
    return carousel


def _slide_image_url(slide: CarouselSlide) -> str | None:
    if not slide.image_mime:
        return None
    ts = int(slide.updated_at.timestamp()) if slide.updated_at else 0
    return f"/api/carousels/{slide.carousel_id}/slides/{slide.id}/image?v={ts}"


def _product_image_url(slide: CarouselSlide) -> str | None:
    if not slide.product_image_mime:
        return None
    ts = int(slide.updated_at.timestamp()) if slide.updated_at else 0
    return f"/api/carousels/{slide.carousel_id}/slides/{slide.id}/product-image?v={ts}"


def _slide_out(slide: CarouselSlide, *, include_admin_fields: bool = True) -> CarouselSlideOut:
    from ..services.carousels import _slide_image_prompt

    layout = slide.layout_json or {}
    prompt = slide.image_prompt
    if include_admin_fields and not (prompt or "").strip():
        prompt = _slide_image_prompt(
            item={"headline": slide.headline or "", "body": slide.body or "", "cta": slide.cta or ""},
            primary=str(layout.get("primary") or "#075985"),
            secondary=str(layout.get("secondary") or "#0f172a"),
            description=slide.body or slide.headline or "",
            related_only=False,
            has_product=bool(slide.product_image_mime),
        )
    return CarouselSlideOut.model_validate(slide).model_copy(
        update={
            "image_url": _slide_image_url(slide),
            "image_prompt": prompt if include_admin_fields else None,
            "image_error": slide.image_error if include_admin_fields else None,
            "product_image_url": _product_image_url(slide) if include_admin_fields else None,
        }
    )


def _is_generating(carousel: Carousel) -> bool:
    if not carousel.generating_at:
        return False
    age = (now_utc() - carousel.generating_at).total_seconds()
    return age < GENERATION_STALE_SECONDS


def _maybe_clear_stale_generating(db: Session, carousel: Carousel) -> None:
    if carousel.generating_at and not _is_generating(carousel):
        carousel.generating_at = None
        db.add(carousel)
        db.commit()


def _assert_client_not_generating(db: Session, client_id: uuid.UUID, *, exclude_carousel_id: uuid.UUID | None = None) -> None:
    rows = db.scalars(select(Carousel).where(Carousel.client_id == client_id)).all()
    for row in rows:
        if exclude_carousel_id and row.id == exclude_carousel_id:
            continue
        if row.generating_at and (now_utc() - row.generating_at).total_seconds() < GENERATION_STALE_SECONDS:
            raise HTTPException(
                status_code=409,
                detail="This client already has a carousel generating. Wait for it to finish or open that carousel.",
            )


def _last_generation_usage(db: Session, carousel_id: uuid.UUID) -> dict | None:
    event = db.scalar(
        select(CarouselEvent)
        .where(
            CarouselEvent.carousel_id == carousel_id,
            CarouselEvent.action.in_(("generate", "regenerate_slide")),
        )
        .order_by(CarouselEvent.created_at.desc())
        .limit(1)
    )
    if not event:
        return None
    usage = (event.payload or {}).get("usage")
    if not usage or not usage.get("items"):
        return None
    return usage


def _carousel_out(carousel: Carousel, *, generation_notes: list[str] | None = None, db: Session | None = None) -> CarouselOut:
    notes = generation_notes if generation_notes is not None else list(getattr(carousel, "_generation_notes", []) or [])
    usage = getattr(carousel, "_generation_usage", None)
    if not usage and db is not None:
        usage = _last_generation_usage(db, carousel.id)
    return CarouselOut(
        id=carousel.id,
        client_id=carousel.client_id,
        title=carousel.title,
        brief=carousel.brief,
        caption=carousel.caption,
        language=carousel.language,
        status=carousel.status,
        slide_count=carousel.slide_count,
        interpret_prompt=bool(getattr(carousel, "interpret_prompt", True)),
        content_goal=getattr(carousel, "content_goal", None) or "loyalty",
        cta_instruction=getattr(carousel, "cta_instruction", None) or "",
        hook_structure=bool(getattr(carousel, "hook_structure", True)),
        scheduled_at=carousel.scheduled_at,
        published_at=carousel.published_at,
        ig_media_id=carousel.ig_media_id,
        publish_error=carousel.publish_error,
        content_item_id=carousel.content_item_id,
        publication_id=carousel.publication_id,
        created_at=carousel.created_at,
        updated_at=carousel.updated_at,
        generating_at=carousel.generating_at,
        is_generating=_is_generating(carousel),
        slides=[_slide_out(s) for s in sorted(carousel.slides, key=lambda x: x.position)],
        generation_notes=notes,
        generation_usage=usage or None,
    )


def _log(db: Session, carousel: Carousel, *, actor_type: str, actor_id, action: str, payload: dict | None = None) -> None:
    db.add(
        CarouselEvent(
            carousel_id=carousel.id,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            payload=payload or {},
        )
    )


@router.get("/image-quote", response_model=ImageCostQuoteOut)
def image_cost_quote(
    count: int = Query(default=1, ge=1, le=12),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List-price estimate for the next image generation (not the invoice)."""
    return quote_image_generation(db, user.agency_id, image_count=count)


@router.get("", response_model=list[CarouselOut])
def list_carousels(client_id: uuid.UUID | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = select(Carousel).options(selectinload(Carousel.slides)).where(Carousel.agency_id == user.agency_id)
    if client_id:
        q = q.where(Carousel.client_id == client_id)
    rows = db.scalars(q.order_by(Carousel.updated_at.desc())).all()
    for row in rows:
        _maybe_clear_stale_generating(db, row)
    return [_carousel_out(row) for row in rows]


@router.post("", response_model=CarouselOut, status_code=status.HTTP_201_CREATED)
def create_carousel(payload: CarouselCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    client = _client_for_agency(db, user, payload.client_id)
    carousel = Carousel(
        agency_id=user.agency_id,
        client_id=client.id,
        created_by_user_id=user.id,
        title=payload.title.strip(),
        brief=payload.brief.strip(),
        language=payload.language,
        slide_count=payload.slide_count,
        interpret_prompt=payload.interpret_prompt,
        content_goal=payload.content_goal,
        cta_instruction=payload.cta_instruction.strip(),
        hook_structure=payload.hook_structure,
        status="draft",
        caption="",
    )
    db.add(carousel)
    db.flush()
    _log(db, carousel, actor_type="agency", actor_id=user.id, action="create")
    db.commit()
    db.refresh(carousel)
    if payload.generate:
        _assert_client_not_generating(db, client.id)
        carousel = generate_carousel_content(
            db,
            carousel,
            client,
            user,
            regenerate=False,
            with_images=payload.with_images,
            interpret_prompt=payload.interpret_prompt,
            ensure_min_image=True,
        )
    else:
        carousel = _carousel_for_agency(db, user, carousel.id)
    return _carousel_out(carousel, db=db)


@router.get("/{carousel_id}", response_model=CarouselOut)
def get_carousel(carousel_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    carousel = _carousel_for_agency(db, user, carousel_id)
    _maybe_clear_stale_generating(db, carousel)
    return _carousel_out(carousel, db=db)


@router.post("/{carousel_id}/generate", response_model=CarouselOut)
def regenerate(
    carousel_id: uuid.UUID,
    payload: CarouselGenerateRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    carousel = _carousel_for_agency(db, user, carousel_id)
    if carousel.status in {"scheduled", "published"}:
        raise HTTPException(status_code=400, detail="Cannot regenerate a scheduled or published carousel")
    client = _client_for_agency(db, user, carousel.client_id)
    body = payload or CarouselGenerateRequest()
    mode = body.interpret_prompt if body.interpret_prompt is not None else carousel.interpret_prompt
    carousel.interpret_prompt = bool(mode)
    apply_playbook_to_carousel(
        carousel,
        content_goal=body.content_goal,
        cta_instruction=body.cta_instruction,
        hook_structure=body.hook_structure,
    )
    db.add(carousel)
    db.commit()
    _assert_client_not_generating(db, carousel.client_id, exclude_carousel_id=carousel.id)
    carousel = generate_carousel_content(
        db,
        carousel,
        client,
        user,
        regenerate=True,
        with_images=body.with_images,
        interpret_prompt=carousel.interpret_prompt,
        ensure_min_image=body.ensure_min_image,
        include_approved=body.include_approved,
    )
    return _carousel_out(carousel, db=db)


@router.patch("/{carousel_id}/slides/{slide_id}", response_model=CarouselSlideOut)
def update_slide(
    carousel_id: uuid.UUID,
    slide_id: uuid.UUID,
    payload: CarouselSlideUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    carousel = _carousel_for_agency(db, user, carousel_id)
    slide = next((s for s in carousel.slides if s.id == slide_id), None)
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(slide, key, value)
    slide.agency_status = "pending"
    slide.client_status = "pending"
    carousel.updated_at = now_utc()
    _log(db, carousel, actor_type="agency", actor_id=user.id, action="edit_slide", payload={"slide_id": str(slide_id)})
    db.commit()
    db.refresh(slide)
    return _slide_out(slide)


@router.post("/{carousel_id}/slides/{slide_id}/generate", response_model=CarouselOut)
def regenerate_slide(
    carousel_id: uuid.UUID,
    slide_id: uuid.UUID,
    payload: CarouselSlideGenerateRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    carousel = _carousel_for_agency(db, user, carousel_id)
    if carousel.status in {"scheduled", "published"}:
        raise HTTPException(status_code=400, detail="Cannot regenerate slides on a scheduled or published carousel")
    slide = next((s for s in carousel.slides if s.id == slide_id), None)
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    client = _client_for_agency(db, user, carousel.client_id)
    body = payload or CarouselSlideGenerateRequest()
    _assert_client_not_generating(db, carousel.client_id, exclude_carousel_id=carousel.id)
    carousel = regenerate_carousel_slide(
        db,
        carousel,
        slide,
        client,
        user,
        with_images=body.with_images,
        image_prompt=body.image_prompt,
        regenerate_copy=body.regenerate_copy,
    )
    return _carousel_out(carousel, db=db)


@router.post("/{carousel_id}/slides/{slide_id}/agency-approve", response_model=CarouselSlideOut)
def agency_approve_slide(
    carousel_id: uuid.UUID,
    slide_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    carousel = _carousel_for_agency(db, user, carousel_id)
    slide = next((s for s in carousel.slides if s.id == slide_id), None)
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    slide.agency_status = "agency_ok"
    _log(db, carousel, actor_type="agency", actor_id=user.id, action="agency_approve_slide", payload={"slide_id": str(slide_id)})
    db.commit()
    db.refresh(slide)
    return _slide_out(slide)


@router.post("/{carousel_id}/slides/{slide_id}/agency-reject", response_model=CarouselSlideOut)
def agency_reject_slide(
    carousel_id: uuid.UUID,
    slide_id: uuid.UUID,
    payload: CarouselSlideDecision | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    carousel = _carousel_for_agency(db, user, carousel_id)
    slide = next((s for s in carousel.slides if s.id == slide_id), None)
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    slide.agency_status = "rejected"
    if payload and payload.comment:
        slide.client_comment = payload.comment
    _log(db, carousel, actor_type="agency", actor_id=user.id, action="agency_reject_slide", payload={"slide_id": str(slide_id)})
    db.commit()
    db.refresh(slide)
    return _slide_out(slide)


@router.post("/{carousel_id}/agency-approve-set", response_model=CarouselOut)
def agency_approve_set(
    carousel_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    carousel = _carousel_for_agency(db, user, carousel_id)
    if carousel.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft carousels can be agency-approved as a set")
    if not carousel.slides:
        raise HTTPException(status_code=400, detail="Generate slides before approving the set")
    for slide in carousel.slides:
        slide.agency_status = "agency_ok"
    _log(db, carousel, actor_type="agency", actor_id=user.id, action="agency_approve_set")
    db.commit()
    return _carousel_out(_carousel_for_agency(db, user, carousel_id))


@router.post("/{carousel_id}/submit-review", response_model=CarouselOut)
def submit_review(carousel_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    carousel = _carousel_for_agency(db, user, carousel_id)
    if not carousel.slides:
        raise HTTPException(status_code=400, detail="Generate slides before submitting for review")
    pending = [s for s in carousel.slides if s.agency_status != "agency_ok"]
    if pending:
        raise HTTPException(status_code=400, detail="Approve all slides before submitting to the client")
    carousel.status = "in_review"
    for slide in carousel.slides:
        slide.client_status = "pending"
    _log(db, carousel, actor_type="agency", actor_id=user.id, action="submit_review")
    db.commit()
    return _carousel_out(_carousel_for_agency(db, user, carousel_id))


@router.post("/{carousel_id}/schedule", response_model=CarouselOut)
def schedule_carousel(
    carousel_id: uuid.UUID,
    payload: CarouselScheduleRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from ..services.carousel_publish_bridge import queue_carousel_publication

    carousel = _carousel_for_agency(db, user, carousel_id)
    if carousel.status != "approved":
        raise HTTPException(status_code=400, detail="Carousel must be client-approved before scheduling")
    queue_carousel_publication(
        db,
        carousel=carousel,
        user=user,
        scheduled_at=payload.scheduled_at,
        timezone_name="UTC",
    )
    db.commit()
    return _carousel_out(_carousel_for_agency(db, user, carousel_id))


@router.post("/{carousel_id}/publish", response_model=CarouselOut)
async def publish_carousel(
    carousel_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Publish an approved carousel to the client's connected Instagram now."""
    from ..services.carousel_publish_bridge import publish_carousel_now

    carousel = _carousel_for_agency(db, user, carousel_id)
    await publish_carousel_now(db, carousel=carousel, user=user)
    return _carousel_out(_carousel_for_agency(db, user, carousel_id))


@router.get("/{carousel_id}/slides/{slide_id}/image")
def get_slide_image(
    carousel_id: uuid.UUID,
    slide_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    carousel = _carousel_for_agency(db, user, carousel_id)
    slide = next((s for s in carousel.slides if s.id == slide_id), None)
    if not slide or not slide.image_data or not slide.image_mime:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(content=slide.image_data, media_type=slide.image_mime, headers={"Cache-Control": "no-store"})


@router.post("/{carousel_id}/slides/{slide_id}/product-image", response_model=CarouselSlideOut)
async def upload_slide_product_image(
    carousel_id: uuid.UUID,
    slide_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    carousel = _carousel_for_agency(db, user, carousel_id)
    slide = next((s for s in carousel.slides if s.id == slide_id), None)
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    if file.content_type not in ALLOWED_PRODUCT_TYPES:
        raise HTTPException(status_code=400, detail="Use a PNG, JPG or WebP product photo")
    data = await file.read(MAX_PRODUCT_BYTES + 1)
    if len(data) > MAX_PRODUCT_BYTES:
        raise HTTPException(status_code=413, detail="The product photo exceeds the 8 MB limit")
    slide.product_image_data = data
    slide.product_image_mime = file.content_type
    slide.updated_at = now_utc()
    carousel.updated_at = now_utc()
    _log(db, carousel, actor_type="agency", actor_id=user.id, action="upload_product_image", payload={"slide_id": str(slide_id)})
    db.commit()
    db.refresh(slide)
    return _slide_out(slide)


@router.get("/{carousel_id}/slides/{slide_id}/product-image")
def get_slide_product_image(
    carousel_id: uuid.UUID,
    slide_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    carousel = _carousel_for_agency(db, user, carousel_id)
    slide = next((s for s in carousel.slides if s.id == slide_id), None)
    if not slide or not slide.product_image_data or not slide.product_image_mime:
        raise HTTPException(status_code=404, detail="Product image not found")
    return Response(
        content=slide.product_image_data,
        media_type=slide.product_image_mime,
        headers={"Cache-Control": "no-store"},
    )


@router.delete("/{carousel_id}/slides/{slide_id}/product-image", response_model=CarouselSlideOut)
def delete_slide_product_image(
    carousel_id: uuid.UUID,
    slide_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    carousel = _carousel_for_agency(db, user, carousel_id)
    slide = next((s for s in carousel.slides if s.id == slide_id), None)
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    slide.product_image_data = None
    slide.product_image_mime = None
    slide.updated_at = now_utc()
    _log(db, carousel, actor_type="agency", actor_id=user.id, action="delete_product_image", payload={"slide_id": str(slide_id)})
    db.commit()
    db.refresh(slide)
    return _slide_out(slide)
