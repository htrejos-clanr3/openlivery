"""Orchestrates Instagram Content Publishing with idempotency and status updates."""

from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from ..models import ContentItem, ContentMedia, InstagramChannel, Publication, User, now_utc
from ..security import decrypt_secret
from .content_service import compose_caption, validate_content_for_publish
from .instagram_errors import classify_instagram_error, humanize_instagram_error
from .instagram_graph import InstagramGraphError, InstagramPublishingProvider, mock_enabled
from .instagram_oauth import has_publish_permission
from .media_public_urls import public_media_url

logger = logging.getLogger(__name__)


def get_channel_or_404(db: Session, user: User, client_id: uuid.UUID) -> InstagramChannel:
    channel = (
        db.query(InstagramChannel)
        .filter(
            InstagramChannel.client_id == client_id,
            InstagramChannel.agency_id == user.agency_id,
        )
        .first()
    )
    if not channel:
        raise HTTPException(status_code=404, detail="Instagram channel not found")
    return channel


def require_connected_channel(channel: InstagramChannel) -> None:
    if channel.status != "connected" or not channel.encrypted_access_token or not channel.instagram_user_id:
        raise HTTPException(status_code=400, detail="Instagram is not connected for this client")
    if not has_publish_permission(channel.granted_scopes) and not mock_enabled():
        raise HTTPException(status_code=400, detail="Missing instagram_content_publish permission. Reconnect with Meta.")


def _provider_for(channel: InstagramChannel) -> InstagramPublishingProvider:
    token = decrypt_secret(channel.encrypted_access_token or "")
    return InstagramPublishingProvider(ig_user_id=channel.instagram_user_id, access_token=token)


async def publish_content(
    db: Session,
    *,
    user: User | None,
    channel: InstagramChannel,
    content: ContentItem,
    publication: Publication | None = None,
) -> Publication:
    require_connected_channel(channel)
    validate_content_for_publish(content)

    if publication is None:
        publication = Publication(
            agency_id=content.agency_id,
            client_id=content.client_id,
            content_id=content.id,
            created_by_user_id=user.id if user else None,
            channel="instagram",
            provider_account_id=channel.instagram_user_id,
            status="QUEUED",
            timezone=content.timezone or "UTC",
        )
        db.add(publication)
        db.flush()

    # Idempotency: already published
    if publication.provider_publication_id and publication.status == "PUBLISHED":
        return publication

    publication.status = "PROCESSING"
    publication.locked_at = now_utc()
    publication.attempt_count = int(publication.attempt_count or 0) + 1
    publication.error_code = None
    publication.error_message = None
    publication.error_class = None
    content.status = "SCHEDULED" if publication.scheduled_at else content.status
    db.commit()

    provider = _provider_for(channel)
    caption = compose_caption(content)
    links = sorted(content.media_links, key=lambda x: x.position)

    try:
        logger.info(
            "instagram_publish_start client_id=%s content_id=%s publication_id=%s ig=%s type=%s",
            content.client_id,
            content.id,
            publication.id,
            channel.instagram_user_id,
            content.content_type,
        )
        container_id: str
        if content.content_type == "IMAGE":
            url = public_media_url(links[0].media_id)
            container_id = await provider.create_image_container(image_url=url, caption=caption)
        elif content.content_type == "CAROUSEL":
            children: list[str] = []
            for link in links:
                media = link.media
                url = public_media_url(media.id)
                if media.mime_type.startswith("video/"):
                    child = await provider.create_video_container(
                        video_url=url, media_type="VIDEO", is_carousel_item=True
                    )
                else:
                    child = await provider.create_image_container(image_url=url, is_carousel_item=True)
                await provider.wait_until_finished(child)
                children.append(child)
            container_id = await provider.create_carousel_container(children=children, caption=caption)
        elif content.content_type == "REEL":
            video = links[0].media
            cover = links[1].media if len(links) > 1 and links[1].media.mime_type.startswith("image/") else None
            container_id = await provider.create_video_container(
                video_url=public_media_url(video.id),
                media_type="REELS",
                caption=caption,
                cover_url=public_media_url(cover.id) if cover else None,
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported content type")

        publication.provider_container_id = container_id
        db.commit()

        await provider.wait_until_finished(container_id)
        media_id = await provider.publish_container(container_id)
        permalink = await provider.get_media_permalink(media_id)

        publication.provider_publication_id = media_id
        publication.provider_permalink = permalink
        publication.status = "PUBLISHED"
        publication.published_at = now_utc()
        publication.locked_at = None
        content.status = "PUBLISHED"
        db.commit()
        logger.info(
            "instagram_publish_ok publication_id=%s media_id=%s",
            publication.id,
            media_id,
        )
        return publication
    except (InstagramGraphError, HTTPException) as exc:
        message = str(exc.detail if isinstance(exc, HTTPException) else exc)
        code = getattr(exc, "code", None) if isinstance(exc, InstagramGraphError) else None
        info = humanize_instagram_error(code=code, message=message)
        publication.status = "FAILED"
        publication.error_code = code
        publication.error_message = info["message"]
        publication.error_class = info["error_class"]
        publication.locked_at = None
        content.status = "FAILED"
        db.commit()
        logger.warning(
            "instagram_publish_fail publication_id=%s class=%s code=%s",
            publication.id,
            publication.error_class,
            code,
        )
        raise HTTPException(status_code=400, detail=info) from exc
    except Exception as exc:  # noqa: BLE001
        info = humanize_instagram_error(message=str(exc))
        publication.status = "FAILED"
        publication.error_message = info["message"]
        publication.error_class = "TRANSIENT"
        publication.locked_at = None
        content.status = "FAILED"
        db.commit()
        raise HTTPException(status_code=500, detail=info) from exc


async def execute_due_publications(db: Session, *, limit: int = 10) -> int:
    """Claim and publish due QUEUED rows. Returns processed count."""
    now = now_utc()
    due = (
        db.query(Publication)
        .options(joinedload(Publication.content).joinedload(ContentItem.media_links).joinedload(ContentMedia.media))
        .filter(
            Publication.channel == "instagram",
            Publication.status == "QUEUED",
            Publication.scheduled_at.isnot(None),
            Publication.scheduled_at <= now,
        )
        .order_by(Publication.scheduled_at.asc())
        .limit(limit)
        .all()
    )
    processed = 0
    for publication in due:
        if publication.provider_publication_id:
            publication.status = "PUBLISHED"
            db.commit()
            continue
        channel = (
            db.query(InstagramChannel)
            .filter(
                InstagramChannel.client_id == publication.client_id,
                InstagramChannel.agency_id == publication.agency_id,
            )
            .first()
        )
        if not channel:
            publication.status = "FAILED"
            publication.error_class = "AUTH"
            publication.error_message = "Instagram channel missing"
            db.commit()
            continue
        content = publication.content
        if not content:
            continue
        # Re-claim atomically
        claimed = (
            db.query(Publication)
            .filter(Publication.id == publication.id, Publication.status == "QUEUED")
            .update(
                {
                    "status": "PROCESSING",
                    "locked_at": now,
                    "attempt_count": int(publication.attempt_count or 0) + 1,
                },
                synchronize_session=False,
            )
        )
        db.commit()
        if not claimed:
            continue
        db.refresh(publication)
        try:
            await publish_content(db, user=None, channel=channel, content=content, publication=publication)
            processed += 1
        except HTTPException:
            # Already persisted failure; optionally requeue transient
            db.refresh(publication)
            if publication.error_class in {"TRANSIENT", "RATE_LIMIT"} and publication.attempt_count < 5:
                publication.status = "QUEUED"
                publication.locked_at = None
                db.commit()
            processed += 1
    return processed
