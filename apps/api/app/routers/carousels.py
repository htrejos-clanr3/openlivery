from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..models import Carousel, CarouselEvent, CarouselSlide, Client, User, now_utc
from ..schemas import (
    CarouselCreate,
    CarouselOut,
    CarouselScheduleRequest,
    CarouselSlideDecision,
    CarouselSlideOut,
    CarouselSlideUpdate,
)
from ..services.carousels import generate_carousel_content


router = APIRouter(prefix="/carousels", tags=["Carousels"])


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


def _slide_out(slide: CarouselSlide) -> CarouselSlideOut:
    return CarouselSlideOut.model_validate(slide)


def _carousel_out(carousel: Carousel) -> CarouselOut:
    return CarouselOut(
        id=carousel.id,
        client_id=carousel.client_id,
        title=carousel.title,
        brief=carousel.brief,
        caption=carousel.caption,
        language=carousel.language,
        status=carousel.status,
        slide_count=carousel.slide_count,
        scheduled_at=carousel.scheduled_at,
        published_at=carousel.published_at,
        ig_media_id=carousel.ig_media_id,
        publish_error=carousel.publish_error,
        created_at=carousel.created_at,
        updated_at=carousel.updated_at,
        slides=[_slide_out(s) for s in sorted(carousel.slides, key=lambda x: x.position)],
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


@router.get("", response_model=list[CarouselOut])
def list_carousels(client_id: uuid.UUID | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = select(Carousel).options(selectinload(Carousel.slides)).where(Carousel.agency_id == user.agency_id)
    if client_id:
        q = q.where(Carousel.client_id == client_id)
    rows = db.scalars(q.order_by(Carousel.updated_at.desc())).all()
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
        status="draft",
        caption="",
    )
    db.add(carousel)
    db.flush()
    _log(db, carousel, actor_type="agency", actor_id=user.id, action="create")
    db.commit()
    db.refresh(carousel)
    if payload.generate:
        carousel = generate_carousel_content(
            db, carousel, client, user, regenerate=False, with_images=payload.with_images
        )
    else:
        carousel = _carousel_for_agency(db, user, carousel.id)
    return _carousel_out(carousel)


@router.get("/{carousel_id}", response_model=CarouselOut)
def get_carousel(carousel_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _carousel_out(_carousel_for_agency(db, user, carousel_id))


@router.post("/{carousel_id}/generate", response_model=CarouselOut)
def regenerate(
    carousel_id: uuid.UUID,
    with_images: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    carousel = _carousel_for_agency(db, user, carousel_id)
    if carousel.status in {"scheduled", "published"}:
        raise HTTPException(status_code=400, detail="Cannot regenerate a scheduled or published carousel")
    client = _client_for_agency(db, user, carousel.client_id)
    carousel = generate_carousel_content(db, carousel, client, user, regenerate=True, with_images=with_images)
    return _carousel_out(carousel)


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
    carousel = _carousel_for_agency(db, user, carousel_id)
    if carousel.status != "approved":
        raise HTTPException(status_code=400, detail="Carousel must be client-approved before scheduling")
    when = payload.scheduled_at
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    if when <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="scheduled_at must be in the future")
    # Instagram channel is not live yet — accept the schedule and mark as scheduled
    # with a clear note until Meta publishing is wired.
    carousel.scheduled_at = when
    carousel.status = "scheduled"
    carousel.publish_error = "Instagram publishing pending: channel not connected yet"
    _log(
        db,
        carousel,
        actor_type="agency",
        actor_id=user.id,
        action="schedule",
        payload={"scheduled_at": when.isoformat(), "ig": "pending"},
    )
    db.commit()
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
