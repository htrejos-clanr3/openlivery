"""Bridge Nico's Carousel approval flow → Instagram Content Publishing.

Approved carousels become ContentItem (CAROUSEL) + MediaAssets + Publication.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from ..models import (
    Carousel,
    CarouselEvent,
    ContentItem,
    ContentMedia,
    InstagramChannel,
    MediaAsset,
    Publication,
    User,
    now_utc,
)
from .instagram_oauth import has_publish_permission
from .instagram_graph import mock_enabled
from .instagram_publishing import publish_content, require_connected_channel


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


def get_instagram_channel(db: Session, *, agency_id: uuid.UUID, client_id: uuid.UUID) -> InstagramChannel | None:
    return (
        db.query(InstagramChannel)
        .filter(InstagramChannel.agency_id == agency_id, InstagramChannel.client_id == client_id)
        .first()
    )


def require_publishable_carousel(carousel: Carousel) -> list:
    slides = sorted(carousel.slides, key=lambda s: s.position)
    if len(slides) < 2:
        raise HTTPException(status_code=400, detail="Carousel needs at least 2 slides to publish on Instagram")
    if len(slides) > 10:
        raise HTTPException(status_code=400, detail="Instagram carousels support at most 10 slides")
    missing = [s.position for s in slides if not s.image_data or not s.image_mime]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Slides without images cannot be published: positions {missing}. Regenerate with images or upload assets.",
        )
    return slides


def require_instagram_ready(channel: InstagramChannel | None) -> InstagramChannel:
    if not channel or channel.status != "connected" or not channel.encrypted_access_token:
        raise HTTPException(
            status_code=400,
            detail="Connect Instagram for this client before scheduling or publishing the carousel.",
        )
    if not has_publish_permission(channel.granted_scopes) and not mock_enabled():
        raise HTTPException(
            status_code=400,
            detail="Instagram is connected but missing publish permission. Reconnect with Meta.",
        )
    require_connected_channel(channel)
    return channel


def materialize_content_from_carousel(
    db: Session,
    *,
    carousel: Carousel,
    user: User,
    channel: InstagramChannel,
) -> ContentItem:
    """Create or refresh a ContentItem + media mirrored from the approved carousel."""
    slides = require_publishable_carousel(carousel)

    if carousel.content_item_id:
        content = (
            db.query(ContentItem)
            .options(joinedload(ContentItem.media_links))
            .filter(ContentItem.id == carousel.content_item_id, ContentItem.agency_id == carousel.agency_id)
            .first()
        )
    else:
        content = None

    if content is None:
        content = ContentItem(
            agency_id=carousel.agency_id,
            client_id=carousel.client_id,
            created_by_user_id=user.id,
            content_type="CAROUSEL",
            status="READY",
            timezone="UTC",
        )
        db.add(content)
        db.flush()
        carousel.content_item_id = content.id

    content.title = carousel.title[:180]
    content.caption = carousel.caption or ""
    content.hashtags = ""
    content.cta = next((s.cta for s in slides if s.cta), "") or ""
    content.ai_meta = {
        "source": "carousel",
        "carousel_id": str(carousel.id),
        "slides": [
            {"order": s.position, "headline": s.headline, "body": s.body, "cta": s.cta}
            for s in slides
        ],
    }
    if content.status not in {"PUBLISHED"}:
        content.status = "READY"

    for link in list(content.media_links):
        db.delete(link)
    db.flush()

    for index, slide in enumerate(slides):
        asset = MediaAsset(
            agency_id=carousel.agency_id,
            client_id=carousel.client_id,
            created_by_user_id=user.id,
            file_name=f"carousel-{carousel.id}-slide-{slide.position}.jpg",
            mime_type=slide.image_mime or "image/jpeg",
            file_size=len(slide.image_data or b""),
            file_data=slide.image_data or b"",
        )
        db.add(asset)
        db.flush()
        db.add(ContentMedia(content_id=content.id, media_id=asset.id, position=index))

    db.flush()
    return content


def queue_carousel_publication(
    db: Session,
    *,
    carousel: Carousel,
    user: User,
    scheduled_at: datetime | None,
    timezone_name: str = "UTC",
) -> Publication:
    channel = require_instagram_ready(get_instagram_channel(db, agency_id=carousel.agency_id, client_id=carousel.client_id))
    content = materialize_content_from_carousel(db, carousel=carousel, user=user, channel=channel)

    if scheduled_at is not None:
        when = scheduled_at
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        when_utc = when.astimezone(timezone.utc)
        if when_utc <= now_utc():
            raise HTTPException(status_code=400, detail="scheduled_at must be in the future")
        publication = Publication(
            agency_id=carousel.agency_id,
            client_id=carousel.client_id,
            content_id=content.id,
            created_by_user_id=user.id,
            channel="instagram",
            provider_account_id=channel.instagram_user_id,
            status="QUEUED",
            scheduled_at=when_utc,
            timezone=timezone_name or "UTC",
        )
        db.add(publication)
        db.flush()
        content.status = "SCHEDULED"
        content.timezone = timezone_name or "UTC"
        carousel.scheduled_at = when_utc
        carousel.status = "scheduled"
        carousel.publish_error = None
        carousel.publication_id = publication.id
        _log(
            db,
            carousel,
            actor_type="agency",
            actor_id=user.id,
            action="schedule",
            payload={
                "scheduled_at": when_utc.isoformat(),
                "publication_id": str(publication.id),
                "content_item_id": str(content.id),
            },
        )
        return publication

    # Immediate path creates a draft publication row; caller runs publish_content.
    publication = Publication(
        agency_id=carousel.agency_id,
        client_id=carousel.client_id,
        content_id=content.id,
        created_by_user_id=user.id,
        channel="instagram",
        provider_account_id=channel.instagram_user_id,
        status="QUEUED",
        timezone=timezone_name or "UTC",
    )
    db.add(publication)
    db.flush()
    carousel.publication_id = publication.id
    carousel.publish_error = None
    return publication


async def publish_carousel_now(db: Session, *, carousel: Carousel, user: User) -> Publication:
    if carousel.status not in {"approved", "failed"}:
        raise HTTPException(status_code=400, detail="Carousel must be client-approved before publishing")
    channel = require_instagram_ready(get_instagram_channel(db, agency_id=carousel.agency_id, client_id=carousel.client_id))
    publication = queue_carousel_publication(db, carousel=carousel, user=user, scheduled_at=None)
    content = (
        db.query(ContentItem)
        .options(joinedload(ContentItem.media_links).joinedload(ContentMedia.media))
        .filter(ContentItem.id == publication.content_id)
        .first()
    )
    assert content is not None
    db.commit()
    try:
        publication = await publish_content(db, user=user, channel=channel, content=content, publication=publication)
    except HTTPException as exc:
        sync_carousel_from_publication(db, publication)
        db.commit()
        raise exc
    sync_carousel_from_publication(db, publication)
    _log(
        db,
        carousel,
        actor_type="agency",
        actor_id=user.id,
        action="publish",
        payload={"publication_id": str(publication.id), "ig_media_id": publication.provider_publication_id},
    )
    db.commit()
    return publication


def sync_carousel_from_publication(db: Session, publication: Publication) -> None:
    """Update Carousel rows when a bridged publication finishes."""
    content = publication.content
    if content is None:
        content = db.query(ContentItem).filter(ContentItem.id == publication.content_id).first()
    if not content:
        return
    meta = content.ai_meta or {}
    if meta.get("source") != "carousel" or not meta.get("carousel_id"):
        # Fallback: carousels pointing at this content/publication
        carousel = (
            db.query(Carousel)
            .filter(
                (Carousel.content_item_id == content.id) | (Carousel.publication_id == publication.id)
            )
            .first()
        )
    else:
        try:
            cid = uuid.UUID(str(meta["carousel_id"]))
        except ValueError:
            return
        carousel = db.query(Carousel).filter(Carousel.id == cid).first()

    if not carousel:
        return

    carousel.publication_id = publication.id
    carousel.content_item_id = content.id
    if publication.status == "PUBLISHED":
        carousel.status = "published"
        carousel.published_at = publication.published_at or now_utc()
        carousel.ig_media_id = publication.provider_publication_id
        carousel.publish_error = None
    elif publication.status == "FAILED":
        carousel.status = "failed"
        carousel.publish_error = publication.error_message or "Instagram publish failed"
    elif publication.status == "QUEUED":
        carousel.status = "scheduled"
        carousel.scheduled_at = publication.scheduled_at
        carousel.publish_error = None
