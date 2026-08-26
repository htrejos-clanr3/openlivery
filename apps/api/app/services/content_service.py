"""Editorial content helpers (CRUD-ish) shared by Instagram publishing routes."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session, joinedload

from ..config import get_settings
from ..models import Client, ContentItem, ContentMedia, MediaAsset, Publication, User, now_utc


IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png"}
VIDEO_TYPES = {"video/mp4", "video/quicktime"}


def get_client_or_404(db: Session, user: User, client_id: uuid.UUID) -> Client:
    client = db.query(Client).filter(Client.id == client_id, Client.agency_id == user.agency_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def get_content_or_404(db: Session, user: User, content_id: uuid.UUID) -> ContentItem:
    content = (
        db.query(ContentItem)
        .options(joinedload(ContentItem.media_links).joinedload(ContentMedia.media))
        .filter(ContentItem.id == content_id, ContentItem.agency_id == user.agency_id)
        .first()
    )
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


async def store_upload(
    db: Session,
    *,
    user: User,
    client: Client,
    upload: UploadFile,
) -> MediaAsset:
    settings = get_settings()
    data = await upload.read()
    mime = (upload.content_type or "application/octet-stream").lower()
    if mime in IMAGE_TYPES and len(data) > settings.instagram_max_image_bytes:
        raise HTTPException(status_code=400, detail="Image exceeds size limit")
    if mime in VIDEO_TYPES and len(data) > settings.instagram_max_video_bytes:
        raise HTTPException(status_code=400, detail="Video exceeds size limit")
    if mime not in IMAGE_TYPES | VIDEO_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported media type: {mime}")
    asset = MediaAsset(
        agency_id=user.agency_id,
        client_id=client.id,
        created_by_user_id=user.id,
        file_name=upload.filename or "upload",
        mime_type=mime,
        file_size=len(data),
        file_data=data,
    )
    db.add(asset)
    db.flush()
    return asset


def set_content_media(db: Session, content: ContentItem, media_ids: list[uuid.UUID]) -> None:
    for link in list(content.media_links):
        db.delete(link)
    db.flush()
    for index, media_id in enumerate(media_ids):
        asset = (
            db.query(MediaAsset)
            .filter(
                MediaAsset.id == media_id,
                MediaAsset.client_id == content.client_id,
                MediaAsset.agency_id == content.agency_id,
            )
            .first()
        )
        if not asset:
            raise HTTPException(status_code=400, detail=f"Media asset not found: {media_id}")
        db.add(ContentMedia(content_id=content.id, media_id=asset.id, position=index))
    db.flush()


def validate_content_for_publish(content: ContentItem) -> None:
    links = sorted(content.media_links, key=lambda x: x.position)
    if content.content_type == "IMAGE":
        if len(links) != 1:
            raise HTTPException(status_code=400, detail="IMAGE requires exactly one media item")
        if links[0].media.mime_type not in IMAGE_TYPES:
            raise HTTPException(status_code=400, detail="IMAGE requires an image file")
    elif content.content_type == "CAROUSEL":
        if not (2 <= len(links) <= 10):
            raise HTTPException(status_code=400, detail="CAROUSEL requires 2–10 media items")
        for link in links:
            if link.media.mime_type not in IMAGE_TYPES | VIDEO_TYPES:
                raise HTTPException(status_code=400, detail="Invalid carousel media type")
    elif content.content_type == "REEL":
        if len(links) < 1:
            raise HTTPException(status_code=400, detail="REEL requires a video")
        if links[0].media.mime_type not in VIDEO_TYPES:
            raise HTTPException(status_code=400, detail="REEL requires a video file")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported content_type: {content.content_type}")


def compose_caption(content: ContentItem) -> str:
    parts = [content.caption.strip()]
    if content.hashtags.strip():
        parts.append(content.hashtags.strip())
    if content.cta.strip():
        parts.append(content.cta.strip())
    return "\n\n".join(p for p in parts if p)


def duplicate_content(db: Session, *, user: User, source: ContentItem) -> ContentItem:
    clone = ContentItem(
        agency_id=source.agency_id,
        client_id=source.client_id,
        created_by_user_id=user.id,
        title=f"Copy of {source.title}"[:180] if source.title else "Copy",
        caption=source.caption,
        hashtags=source.hashtags,
        cta=source.cta,
        content_type=source.content_type,
        status="DRAFT",
        timezone=source.timezone,
        ai_meta=dict(source.ai_meta or {}),
    )
    db.add(clone)
    db.flush()
    for link in sorted(source.media_links, key=lambda x: x.position):
        db.add(ContentMedia(content_id=clone.id, media_id=link.media_id, position=link.position))
    db.flush()
    return clone


def latest_publication(db: Session, content_id: uuid.UUID) -> Publication | None:
    return (
        db.query(Publication)
        .filter(Publication.content_id == content_id)
        .order_by(Publication.created_at.desc())
        .first()
    )


def touch(content: ContentItem) -> None:
    content.updated_at = now_utc()
