"""Instagram channel connection + Content Publishing APIs (no DM/messaging)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import get_current_user
from ..models import (
    Client,
    ContentItem,
    ContentMedia,
    InstagramChannel,
    MediaAsset,
    Publication,
    User,
    now_utc,
)
from ..schemas_instagram import (
    ContentItemCreate,
    ContentItemOut,
    ContentItemUpdate,
    ContentMediaOut,
    DashboardStatsOut,
    GenerateContentOut,
    GenerateContentRequest,
    InstagramAccountChoiceOut,
    InstagramChannelManualUpdate,
    InstagramChannelOut,
    InstagramHealthOut,
    InstagramOAuthCompleteIn,
    InstagramOAuthOptionsOut,
    InstagramOAuthSessionIn,
    InstagramOAuthSessionOut,
    InstagramPublishingLimitOut,
    MediaAssetOut,
    PublishApprovalBody,
    PublicationOut,
    ScheduleRequest,
)
from ..security import decrypt_secret, encrypt_secret
from ..services import instagram_oauth
from ..services.legal_consent import (
    record_channel_connect_consent,
    record_publish_approval,
    require_publish_approval,
)
from ..services.content_service import (
    duplicate_content,
    get_client_or_404,
    get_content_or_404,
    set_content_media,
    store_upload,
    touch,
)
from ..services.instagram_graph import InstagramGraphError, InstagramPublishingProvider, mock_enabled
from ..services.instagram_publishing import get_channel_or_404, publish_content, require_connected_channel
from ..services.media_public_urls import verify_media_signature
from ..services.social_content_generation import generate_social_content


router = APIRouter(prefix="/instagram", tags=["Instagram Publishing"])
public_router = APIRouter(prefix="/public", tags=["Public Media"])


def _channel_out(channel: InstagramChannel) -> InstagramChannelOut:
    scopes = list(channel.granted_scopes or [])
    return InstagramChannelOut(
        id=channel.id,
        client_id=channel.client_id,
        status=channel.status,
        instagram_user_id=channel.instagram_user_id or "",
        page_id=channel.page_id,
        username=channel.username,
        display_name=channel.display_name,
        access_token_configured=bool(channel.encrypted_access_token),
        token_expires_at=channel.token_expires_at,
        granted_scopes=scopes,
        connection_mode=channel.connection_mode,
        last_error=channel.last_error,
        is_enabled=channel.is_enabled,
        last_connected_at=channel.last_connected_at,
        publish_permission=instagram_oauth.has_publish_permission(scopes) or mock_enabled(),
    )


def _media_preview(asset: MediaAsset) -> str:
    return f"/api/instagram/media/{asset.id}/preview"


def _media_out(asset: MediaAsset) -> MediaAssetOut:
    return MediaAssetOut(
        id=asset.id,
        client_id=asset.client_id,
        file_name=asset.file_name,
        mime_type=asset.mime_type,
        file_size=asset.file_size,
        width=asset.width,
        height=asset.height,
        duration=asset.duration,
        created_at=asset.created_at,
        preview_url=_media_preview(asset),
    )


def _content_out(content: ContentItem) -> ContentItemOut:
    media = []
    for link in sorted(content.media_links, key=lambda x: x.position):
        asset = link.media
        media.append(
            ContentMediaOut(
                media_id=link.media_id,
                position=link.position,
                file_name=asset.file_name if asset else None,
                mime_type=asset.mime_type if asset else None,
                preview_url=_media_preview(asset) if asset else None,
            )
        )
    return ContentItemOut(
        id=content.id,
        client_id=content.client_id,
        title=content.title,
        caption=content.caption,
        hashtags=content.hashtags,
        cta=content.cta,
        content_type=content.content_type,
        status=content.status,
        timezone=content.timezone,
        ai_meta=content.ai_meta or {},
        media=media,
        created_at=content.created_at,
        updated_at=content.updated_at,
    )


def _ensure_channel(db: Session, user: User, client: Client) -> InstagramChannel:
    channel = (
        db.query(InstagramChannel)
        .filter(InstagramChannel.client_id == client.id, InstagramChannel.agency_id == user.agency_id)
        .first()
    )
    if not channel:
        channel = InstagramChannel(agency_id=user.agency_id, client_id=client.id, status="disconnected")
        db.add(channel)
        db.commit()
        db.refresh(channel)
    return channel


def _apply_account(
    channel: InstagramChannel,
    *,
    account: dict,
    scopes: list[str],
    mode: str,
    expires_in: int | None = None,
) -> None:
    channel.instagram_user_id = str(account["instagram_user_id"])
    channel.page_id = account.get("page_id")
    channel.username = account.get("username")
    channel.display_name = account.get("display_name") or account.get("username")
    channel.encrypted_access_token = encrypt_secret(account["page_access_token"])
    channel.granted_scopes = scopes
    channel.connection_mode = mode
    channel.status = "connected"
    channel.last_error = None
    channel.last_connected_at = now_utc()
    if expires_in:
        channel.token_expires_at = now_utc() + timedelta(seconds=int(expires_in))


# --- Channel / OAuth ---------------------------------------------------------


@router.get("/oauth/options", response_model=InstagramOAuthOptionsOut)
def oauth_options(user: User = Depends(get_current_user)):
    return InstagramOAuthOptionsOut(**instagram_oauth.oauth_options())


@router.get("/channels/{client_id}", response_model=InstagramChannelOut)
def get_channel(client_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    client = get_client_or_404(db, user, client_id)
    channel = _ensure_channel(db, user, client)
    return _channel_out(channel)


@router.put("/channels/{client_id}", response_model=InstagramChannelOut)
def configure_manual(
    client_id: uuid.UUID,
    payload: InstagramChannelManualUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = get_client_or_404(db, user, client_id)
    channel = _ensure_channel(db, user, client)
    channel.instagram_user_id = payload.instagram_user_id.strip()
    channel.page_id = payload.page_id
    channel.username = payload.username
    channel.display_name = payload.display_name or payload.username
    if payload.access_token and payload.access_token.strip():
        channel.encrypted_access_token = encrypt_secret(payload.access_token.strip())
    if payload.granted_scopes is not None:
        channel.granted_scopes = payload.granted_scopes
    elif not channel.granted_scopes:
        channel.granted_scopes = list(instagram_oauth.DEFAULT_SCOPES)
    channel.connection_mode = "manual"
    if channel.encrypted_access_token and channel.instagram_user_id:
        channel.status = "connected"
        channel.last_connected_at = now_utc()
        channel.last_error = None
    db.commit()
    db.refresh(channel)
    return _channel_out(channel)


@router.post("/channels/{client_id}/oauth/session", response_model=InstagramOAuthSessionOut)
def start_oauth_session(
    client_id: uuid.UUID,
    payload: InstagramOAuthSessionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = get_client_or_404(db, user, client_id)
    _ensure_channel(db, user, client)
    if payload.consent.client_id != client_id:
        raise HTTPException(status_code=400, detail="Consent client mismatch")
    record_channel_connect_consent(db, user=user, payload=payload.consent)
    options = instagram_oauth.oauth_options()
    if not options["oauth_available"]:
        raise HTTPException(status_code=400, detail=options["blocked_reason"] or "OAuth unavailable")
    state = instagram_oauth.create_oauth_state(
        agency_id=str(user.agency_id),
        client_id=str(client.id),
        user_id=str(user.id),
    )
    return InstagramOAuthSessionOut(
        state=state,
        dialog_url=instagram_oauth.build_oauth_dialog_url(state),
        mock_mode=bool(options["mock_mode"]),
    )


@router.post("/channels/{client_id}/oauth/complete", response_model=InstagramChannelOut)
async def complete_oauth(
    client_id: uuid.UUID,
    payload: InstagramOAuthCompleteIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = get_client_or_404(db, user, client_id)
    channel = _ensure_channel(db, user, client)
    state = instagram_oauth.parse_oauth_state(payload.state)
    if state["client_id"] != str(client.id) or state["agency_id"] != str(user.agency_id):
        raise HTTPException(status_code=400, detail="OAuth state client mismatch")

    use_mock = payload.use_mock or mock_enabled()
    if use_mock:
        accounts = await instagram_oauth.discover_instagram_accounts("mock")
        account = accounts[0]
        _apply_account(
            channel,
            account=account,
            scopes=list(instagram_oauth.DEFAULT_SCOPES),
            mode="mock",
            expires_in=60 * 60 * 24 * 60,
        )
        db.commit()
        db.refresh(channel)
        return _channel_out(channel)

    if not payload.code:
        raise HTTPException(status_code=400, detail="Missing OAuth code")
    token_payload = await instagram_oauth.exchange_code_for_token(payload.code)
    long_lived = await instagram_oauth.exchange_long_lived_user_token(token_payload["access_token"])
    user_token = long_lived["access_token"]
    accounts = await instagram_oauth.discover_instagram_accounts(user_token)
    if not accounts:
        raise HTTPException(status_code=400, detail="No Instagram professional accounts found on your Pages")
    account = accounts[0]
    if payload.instagram_user_id:
        match = next((a for a in accounts if a["instagram_user_id"] == payload.instagram_user_id), None)
        if not match:
            raise HTTPException(status_code=400, detail="Selected Instagram account not available")
        account = match
    _apply_account(
        channel,
        account=account,
        scopes=list(instagram_oauth.DEFAULT_SCOPES),
        mode="oauth",
        expires_in=long_lived.get("expires_in"),
    )
    db.commit()
    db.refresh(channel)
    return _channel_out(channel)


@router.get("/channels/{client_id}/accounts", response_model=list[InstagramAccountChoiceOut])
async def list_accounts_after_token(
    client_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Diagnostic: list IG accounts using the stored token (manual/oauth)."""
    channel = get_channel_or_404(db, user, client_id)
    if not channel.encrypted_access_token:
        return []
    if mock_enabled() or channel.connection_mode == "mock":
        accounts = await instagram_oauth.discover_instagram_accounts("mock")
    else:
        # Stored token is Page token; discovery needs user token — return current only.
        return [
            InstagramAccountChoiceOut(
                page_id=channel.page_id,
                page_name=None,
                instagram_user_id=channel.instagram_user_id,
                username=channel.username,
                display_name=channel.display_name,
            )
        ]
    return [InstagramAccountChoiceOut(**{k: a.get(k) for k in ("page_id", "page_name", "instagram_user_id", "username", "display_name")}) for a in accounts]


@router.post("/channels/{client_id}/disconnect", response_model=InstagramChannelOut)
def disconnect_channel(
    client_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    channel = get_channel_or_404(db, user, client_id)
    channel.encrypted_access_token = None
    channel.status = "disconnected"
    channel.last_error = None
    db.commit()
    db.refresh(channel)
    return _channel_out(channel)


@router.get("/channels/{client_id}/health", response_model=InstagramHealthOut)
async def channel_health(
    client_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    channel = get_channel_or_404(db, user, client_id)
    token_ok = bool(channel.encrypted_access_token)
    account_ok = bool(channel.instagram_user_id)
    publish_ok = instagram_oauth.has_publish_permission(channel.granted_scopes) or mock_enabled()
    api_ok = False
    details: dict = {}
    if token_ok and account_ok:
        try:
            provider = InstagramPublishingProvider(
                ig_user_id=channel.instagram_user_id,
                access_token=decrypt_secret(channel.encrypted_access_token or ""),
            )
            me = await provider.debug_token_or_me()
            api_ok = True
            details["profile"] = me
        except InstagramGraphError as exc:
            details["error"] = str(exc)
            channel.last_error = str(exc)
            db.commit()
    ui = "disconnected"
    if channel.status == "connected" and token_ok and account_ok and api_ok:
        ui = "ok" if publish_ok else "partial"
    elif channel.status == "connected":
        ui = "error"
    return InstagramHealthOut(
        ui_status=ui,
        account_ok=account_ok,
        token_ok=token_ok,
        publish_permission_ok=publish_ok,
        api_ok=api_ok,
        mock_mode=mock_enabled() or channel.connection_mode == "mock",
        details=details,
    )


@router.get("/channels/{client_id}/publishing-limit", response_model=InstagramPublishingLimitOut)
async def publishing_limit(
    client_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    channel = get_channel_or_404(db, user, client_id)
    if channel.status != "connected" or not channel.encrypted_access_token:
        return InstagramPublishingLimitOut(available=False)
    try:
        provider = InstagramPublishingProvider(
            ig_user_id=channel.instagram_user_id,
            access_token=decrypt_secret(channel.encrypted_access_token),
        )
        data = await provider.content_publishing_limit()
        config = data.get("config") or {}
        return InstagramPublishingLimitOut(
            quota_usage=int(data.get("quota_usage") or 0),
            quota_total=int(config.get("quota_total") or 0) or None,
            quota_duration=int(config.get("quota_duration") or 0) or None,
            available=True,
        )
    except InstagramGraphError:
        return InstagramPublishingLimitOut(available=False)


@router.get("/oauth/callback")
async def oauth_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    """Browser lander: bounce query params to the SPA Instagram channel page."""
    from ..config import get_settings

    settings = get_settings()
    if error:
        return RedirectResponse(f"{settings.frontend_url}/channels?instagram_error={error}")
    # State embeds client_id — parse carefully
    client_id = ""
    if state:
        try:
            parsed = instagram_oauth.parse_oauth_state(state)
            client_id = parsed.get("client_id") or ""
        except HTTPException:
            client_id = ""
    if not client_id:
        return RedirectResponse(f"{settings.frontend_url}/channels?instagram_error=missing_state")
    q = f"oauth_code={code or ''}&oauth_state={state or ''}"
    return RedirectResponse(f"{settings.frontend_url}/clients/{client_id}/channels/instagram?{q}")


# --- Media library -----------------------------------------------------------


@router.get("/channels/{client_id}/media", response_model=list[MediaAssetOut])
def list_media(
    client_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_client_or_404(db, user, client_id)
    rows = (
        db.query(MediaAsset)
        .filter(MediaAsset.client_id == client_id, MediaAsset.agency_id == user.agency_id)
        .order_by(MediaAsset.created_at.desc())
        .limit(200)
        .all()
    )
    return [_media_out(r) for r in rows]


@router.post("/channels/{client_id}/media", response_model=MediaAssetOut)
async def upload_media(
    client_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = get_client_or_404(db, user, client_id)
    asset = await store_upload(db, user=user, client=client, upload=file)
    db.commit()
    db.refresh(asset)
    return _media_out(asset)


@router.get("/media/{media_id}/preview")
def preview_media(media_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    asset = (
        db.query(MediaAsset)
        .filter(MediaAsset.id == media_id, MediaAsset.agency_id == user.agency_id)
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Media not found")
    return Response(content=asset.file_data, media_type=asset.mime_type)


@router.delete("/channels/{client_id}/media/{media_id}")
def delete_media(
    client_id: uuid.UUID,
    media_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_client_or_404(db, user, client_id)
    asset = (
        db.query(MediaAsset)
        .filter(MediaAsset.id == media_id, MediaAsset.client_id == client_id, MediaAsset.agency_id == user.agency_id)
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Media not found")
    in_use = db.query(ContentMedia).filter(ContentMedia.media_id == media_id).first()
    if in_use:
        raise HTTPException(status_code=400, detail="Media is used by content and cannot be deleted")
    db.delete(asset)
    db.commit()
    return {"ok": True}


@public_router.get("/media-assets/{media_id}")
def public_media(media_id: uuid.UUID, exp: int = Query(...), sig: str = Query(...), db: Session = Depends(get_db)):
    verify_media_signature(media_id, exp, sig)
    asset = db.query(MediaAsset).filter(MediaAsset.id == media_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Media not found")
    return Response(content=asset.file_data, media_type=asset.mime_type)


# --- Content + publications --------------------------------------------------


@router.get("/channels/{client_id}/dashboard", response_model=DashboardStatsOut)
def dashboard_stats(
    client_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_client_or_404(db, user, client_id)
    month_start = now_utc().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    drafts = (
        db.query(func.count(ContentItem.id))
        .filter(ContentItem.client_id == client_id, ContentItem.agency_id == user.agency_id, ContentItem.status == "DRAFT")
        .scalar()
        or 0
    )
    scheduled = (
        db.query(func.count(Publication.id))
        .filter(
            Publication.client_id == client_id,
            Publication.agency_id == user.agency_id,
            Publication.status == "QUEUED",
        )
        .scalar()
        or 0
    )
    published_month = (
        db.query(func.count(Publication.id))
        .filter(
            Publication.client_id == client_id,
            Publication.agency_id == user.agency_id,
            Publication.status == "PUBLISHED",
            Publication.published_at >= month_start,
        )
        .scalar()
        or 0
    )
    failed = (
        db.query(func.count(Publication.id))
        .filter(
            Publication.client_id == client_id,
            Publication.agency_id == user.agency_id,
            Publication.status == "FAILED",
        )
        .scalar()
        or 0
    )
    return DashboardStatsOut(
        drafts=int(drafts),
        scheduled=int(scheduled),
        published_month=int(published_month),
        failed=int(failed),
    )


@router.get("/channels/{client_id}/content", response_model=list[ContentItemOut])
def list_content(
    client_id: uuid.UUID,
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_client_or_404(db, user, client_id)
    q = (
        db.query(ContentItem)
        .options(joinedload(ContentItem.media_links).joinedload(ContentMedia.media))
        .filter(ContentItem.client_id == client_id, ContentItem.agency_id == user.agency_id)
    )
    if status:
        q = q.filter(ContentItem.status == status)
    rows = q.order_by(ContentItem.updated_at.desc()).limit(100).all()
    return [_content_out(r) for r in rows]


@router.post("/channels/{client_id}/content", response_model=ContentItemOut)
def create_content(
    client_id: uuid.UUID,
    payload: ContentItemCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = get_client_or_404(db, user, client_id)
    content_type = payload.content_type.upper()
    if content_type not in {"IMAGE", "CAROUSEL", "REEL"}:
        raise HTTPException(status_code=400, detail="content_type must be IMAGE, CAROUSEL, or REEL")
    content = ContentItem(
        agency_id=user.agency_id,
        client_id=client.id,
        created_by_user_id=user.id,
        title=payload.title,
        caption=payload.caption,
        hashtags=payload.hashtags,
        cta=payload.cta,
        content_type=content_type,
        status="DRAFT",
        timezone=payload.timezone or "UTC",
    )
    db.add(content)
    db.flush()
    if payload.media_ids:
        set_content_media(db, content, payload.media_ids)
    db.commit()
    db.expire_all()
    content = get_content_or_404(db, user, content.id)
    return _content_out(content)


@router.get("/channels/{client_id}/content/{content_id}", response_model=ContentItemOut)
def get_content(
    client_id: uuid.UUID,
    content_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_client_or_404(db, user, client_id)
    content = get_content_or_404(db, user, content_id)
    if content.client_id != client_id:
        raise HTTPException(status_code=404, detail="Content not found")
    return _content_out(content)


@router.put("/channels/{client_id}/content/{content_id}", response_model=ContentItemOut)
def update_content(
    client_id: uuid.UUID,
    content_id: uuid.UUID,
    payload: ContentItemUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_client_or_404(db, user, client_id)
    content = get_content_or_404(db, user, content_id)
    if content.client_id != client_id:
        raise HTTPException(status_code=404, detail="Content not found")
    if content.status == "PUBLISHED":
        raise HTTPException(status_code=400, detail="Published content is immutable; duplicate instead")
    if payload.title is not None:
        content.title = payload.title
    if payload.caption is not None:
        content.caption = payload.caption
    if payload.hashtags is not None:
        content.hashtags = payload.hashtags
    if payload.cta is not None:
        content.cta = payload.cta
    if payload.timezone is not None:
        content.timezone = payload.timezone
    if payload.status is not None:
        content.status = payload.status
    if payload.ai_meta is not None:
        content.ai_meta = payload.ai_meta
    if payload.media_ids is not None:
        set_content_media(db, content, payload.media_ids)
    touch(content)
    db.commit()
    db.expire_all()
    content = get_content_or_404(db, user, content.id)
    return _content_out(content)


@router.post("/channels/{client_id}/content/{content_id}/duplicate", response_model=ContentItemOut)
def duplicate(
    client_id: uuid.UUID,
    content_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_client_or_404(db, user, client_id)
    source = get_content_or_404(db, user, content_id)
    if source.client_id != client_id:
        raise HTTPException(status_code=404, detail="Content not found")
    clone = duplicate_content(db, user=user, source=source)
    db.commit()
    clone = get_content_or_404(db, user, clone.id)
    return _content_out(clone)


@router.post("/channels/{client_id}/content/{content_id}/publish", response_model=PublicationOut)
async def publish_now(
    client_id: uuid.UUID,
    content_id: uuid.UUID,
    payload: PublishApprovalBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_client_or_404(db, user, client_id)
    channel = get_channel_or_404(db, user, client_id)
    content = get_content_or_404(db, user, content_id)
    if content.client_id != client_id:
        raise HTTPException(status_code=404, detail="Content not found")
    require_publish_approval(
        human_approved=payload.human_approved,
        reviewed_exact_content=payload.reviewed_exact_content,
    )
    record_publish_approval(
        db,
        user=user,
        client_id=client_id,
        channel="instagram",
        content_id=content_id,
        metadata={"username": channel.username or ""},
    )
    publication = await publish_content(db, user=user, channel=channel, content=content)
    db.commit()
    return PublicationOut.model_validate(publication)


@router.post("/channels/{client_id}/content/{content_id}/schedule", response_model=PublicationOut)
def schedule_publish(
    client_id: uuid.UUID,
    content_id: uuid.UUID,
    payload: ScheduleRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_client_or_404(db, user, client_id)
    channel = get_channel_or_404(db, user, client_id)
    require_connected_channel(channel)
    content = get_content_or_404(db, user, content_id)
    if content.client_id != client_id:
        raise HTTPException(status_code=404, detail="Content not found")
    require_publish_approval(
        human_approved=payload.human_approved,
        reviewed_exact_content=payload.reviewed_exact_content,
    )
    record_publish_approval(
        db,
        user=user,
        client_id=client_id,
        channel="instagram",
        content_id=content_id,
        metadata={"username": channel.username or "", "scheduled": True},
    )
    when = payload.scheduled_at
    if when.tzinfo is None:
        try:
            when = when.replace(tzinfo=ZoneInfo(payload.timezone or "UTC"))
        except Exception:  # noqa: BLE001
            when = when.replace(tzinfo=timezone.utc)
    when_utc = when.astimezone(timezone.utc)
    if when_utc <= now_utc():
        raise HTTPException(status_code=400, detail="scheduled_at must be in the future")
    content.timezone = payload.timezone or content.timezone or "UTC"
    content.status = "SCHEDULED"
    publication = Publication(
        agency_id=user.agency_id,
        client_id=client_id,
        content_id=content.id,
        created_by_user_id=user.id,
        channel="instagram",
        provider_account_id=channel.instagram_user_id,
        status="QUEUED",
        scheduled_at=when_utc,
        timezone=content.timezone,
    )
    db.add(publication)
    db.commit()
    db.refresh(publication)
    return PublicationOut.model_validate(publication)


@router.get("/channels/{client_id}/publications", response_model=list[PublicationOut])
def list_publications(
    client_id: uuid.UUID,
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_client_or_404(db, user, client_id)
    q = db.query(Publication).filter(Publication.client_id == client_id, Publication.agency_id == user.agency_id)
    if status:
        q = q.filter(Publication.status == status)
    rows = q.order_by(Publication.created_at.desc()).limit(100).all()
    return [PublicationOut.model_validate(r) for r in rows]


@router.post("/channels/{client_id}/generate", response_model=GenerateContentOut)
async def generate_copy(
    client_id: uuid.UUID,
    payload: GenerateContentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = get_client_or_404(db, user, client_id)
    data = await generate_social_content(
        db,
        client=client,
        content_type=payload.content_type.upper(),
        objective=payload.objective,
        audience=payload.audience,
        user_instruction=payload.user_instruction,
        slide_count=payload.slide_count,
        language=payload.language,
    )
    return GenerateContentOut(**data)
