"""LinkedIn copy desk and official personal-profile text publishing."""

from __future__ import annotations

import uuid
from datetime import timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import LinkedInChannel, LinkedInDraft, User, now_utc
from ..schemas_linkedin import (
    LinkedInChannelOut,
    LinkedInChannelUpdate,
    LinkedInDraftOut,
    LinkedInGeneratePostRequest,
    LinkedInHumanizeRequest,
    LinkedInOAuthCompleteIn,
    LinkedInOAuthOptionsOut,
    LinkedInOAuthSessionOut,
    LinkedInPublicationOut,
    LinkedInProfileRequest,
    LinkedInPublishRequest,
)
from ..security import decrypt_secret, encrypt_secret
from ..services.content_service import get_client_or_404
from ..services.linkedin.generate import clean_text, generate_post, load_hooks, rewrite_profile, score_profile_heuristic
from ..services.linkedin import oauth as linkedin_oauth
from ..services.linkedin.publishing import LinkedInPublishingError, LinkedInPublishingProvider


router = APIRouter(prefix="/linkedin", tags=["LinkedIn"])


def _get_or_create_channel(db: Session, user: User, client_id: uuid.UUID) -> LinkedInChannel:
    client = get_client_or_404(db, user, client_id)
    channel = db.scalar(select(LinkedInChannel).where(LinkedInChannel.client_id == client.id))
    if channel:
        return channel
    channel = LinkedInChannel(agency_id=user.agency_id, client_id=client.id, display_name=client.name)
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


def _channel_out(channel: LinkedInChannel) -> LinkedInChannelOut:
    scopes = list(channel.granted_scopes or [])
    can_publish = (
        channel.status == "connected"
        and bool(channel.encrypted_access_token)
        and bool(channel.member_id)
        and ("w_member_social" in scopes or linkedin_oauth.mock_enabled())
    )
    return LinkedInChannelOut(
        id=channel.id,
        client_id=channel.client_id,
        profile_url=channel.profile_url or "",
        display_name=channel.display_name or "",
        voice_notes=channel.voice_notes or "",
        status=channel.status,
        member_id=channel.member_id or "",
        access_token_configured=bool(channel.encrypted_access_token),
        granted_scopes=scopes,
        token_expires_at=channel.token_expires_at,
        last_error=channel.last_error,
        last_connected_at=channel.last_connected_at,
        is_enabled=channel.is_enabled,
        publishes=can_publish,
        connection_mode=channel.connection_mode,
        updated_at=channel.updated_at,
    )


def _apply_oauth(
    channel: LinkedInChannel,
    *,
    member: dict,
    token: dict,
    mode: str,
) -> None:
    channel.member_id = str(member["sub"])
    channel.display_name = str(member.get("name") or channel.display_name or "")
    channel.encrypted_access_token = encrypt_secret(str(token["access_token"]))
    raw_scope = token.get("scope") or " ".join(linkedin_oauth.DEFAULT_SCOPES)
    channel.granted_scopes = raw_scope.split() if isinstance(raw_scope, str) else list(raw_scope)
    channel.token_expires_at = (
        now_utc() + timedelta(seconds=int(token["expires_in"])) if token.get("expires_in") else None
    )
    channel.connection_mode = mode
    channel.status = "connected"
    channel.last_error = None
    channel.last_connected_at = now_utc()


@router.get("/channels/{client_id}", response_model=LinkedInChannelOut)
def get_channel(client_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _channel_out(_get_or_create_channel(db, user, client_id))


@router.patch("/channels/{client_id}", response_model=LinkedInChannelOut)
def update_channel(
    client_id: uuid.UUID,
    payload: LinkedInChannelUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    channel = _get_or_create_channel(db, user, client_id)
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(channel, key, value if value is not None else getattr(channel, key))
    channel.updated_at = now_utc()
    db.commit()
    db.refresh(channel)
    return _channel_out(channel)


@router.get("/oauth/options", response_model=LinkedInOAuthOptionsOut)
def oauth_options(user: User = Depends(get_current_user)):
    return LinkedInOAuthOptionsOut(**linkedin_oauth.oauth_options())


@router.post("/channels/{client_id}/oauth/session", response_model=LinkedInOAuthSessionOut)
def start_oauth_session(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_or_create_channel(db, user, client_id)
    options = linkedin_oauth.oauth_options()
    if not options["oauth_available"]:
        raise HTTPException(status_code=400, detail=options["blocked_reason"] or "LinkedIn OAuth unavailable")
    state = linkedin_oauth.create_oauth_state(
        agency_id=str(user.agency_id),
        client_id=str(client_id),
        user_id=str(user.id),
    )
    return LinkedInOAuthSessionOut(
        state=state,
        dialog_url=linkedin_oauth.build_oauth_dialog_url(state),
        mock_mode=bool(options["mock_mode"]),
    )


@router.post("/channels/{client_id}/oauth/complete", response_model=LinkedInChannelOut)
async def complete_oauth(
    client_id: uuid.UUID,
    payload: LinkedInOAuthCompleteIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    channel = _get_or_create_channel(db, user, client_id)
    state = linkedin_oauth.parse_oauth_state(payload.state)
    if (
        state.get("client_id") != str(client_id)
        or state.get("agency_id") != str(user.agency_id)
        or state.get("user_id") != str(user.id)
    ):
        raise HTTPException(status_code=400, detail="LinkedIn OAuth state mismatch")
    use_mock = payload.use_mock or linkedin_oauth.mock_enabled()
    if not use_mock and not payload.code:
        raise HTTPException(status_code=400, detail="Missing LinkedIn OAuth code")
    try:
        token = await linkedin_oauth.exchange_code_for_token(payload.code or "mock")
        member = await linkedin_oauth.fetch_member(str(token["access_token"]))
        _apply_oauth(channel, member=member, token=token, mode="mock" if use_mock else "oauth")
        db.commit()
        db.refresh(channel)
        return _channel_out(channel)
    except HTTPException as exc:
        channel.status = "error"
        channel.last_error = str(exc.detail)
        db.commit()
        raise


@router.get("/oauth/callback")
def oauth_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    settings = get_settings()
    client_id = ""
    if state:
        try:
            client_id = str(linkedin_oauth.parse_oauth_state(state).get("client_id") or "")
        except HTTPException:
            client_id = ""
    if not client_id:
        query = urlencode({"linkedin_error": error or "missing_state"})
        return RedirectResponse(f"{settings.frontend_url.rstrip('/')}/channels?{query}")
    query = urlencode(
        {
            "oauth_code": code or "",
            "oauth_state": state or "",
            "linkedin_error": error or "",
        }
    )
    return RedirectResponse(
        f"{settings.frontend_url.rstrip('/')}/clients/{client_id}/channels/linkedin?{query}"
    )


@router.post("/channels/{client_id}/disconnect", response_model=LinkedInChannelOut)
def disconnect_channel(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    channel = _get_or_create_channel(db, user, client_id)
    channel.status = "disconnected"
    channel.member_id = ""
    channel.encrypted_access_token = None
    channel.granted_scopes = []
    channel.token_expires_at = None
    channel.connection_mode = "copy_paste"
    channel.last_error = None
    db.commit()
    db.refresh(channel)
    return _channel_out(channel)


@router.get("/hooks")
def list_hooks(user: User = Depends(get_current_user)):
    return load_hooks()


@router.post("/channels/{client_id}/humanize")
def humanize_text(
    client_id: uuid.UUID,
    payload: LinkedInHumanizeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_client_or_404(db, user, client_id)
    cleaned, report, panel = clean_text(payload.text)
    return {"text": cleaned, "report": report, "panel": panel}


@router.post("/channels/{client_id}/posts")
async def create_post(
    client_id: uuid.UUID,
    payload: LinkedInGeneratePostRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    channel = _get_or_create_channel(db, user, client_id)
    client = get_client_or_404(db, user, client_id)
    result = await generate_post(
        db, client=client, idea=payload.idea, voice_notes=channel.voice_notes, language=payload.language
    )
    panel = (result.get("humanize") or {}).get("panel") or {}
    draft = LinkedInDraft(
        agency_id=user.agency_id,
        channel_id=channel.id,
        kind="post",
        idea=payload.idea.strip(),
        body=result.get("copy_ready") or "",
        hook_id=result.get("chosen_hook_id"),
        human_score=panel.get("human_score"),
        verdict=panel.get("verdict") or "",
        payload=result,
    )
    db.add(draft)
    db.commit()
    result["draft_id"] = str(draft.id)
    return result


@router.post("/channels/{client_id}/profile")
async def profile_rewrite(
    client_id: uuid.UUID,
    payload: LinkedInProfileRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    channel = _get_or_create_channel(db, user, client_id)
    client = get_client_or_404(db, user, client_id)
    result = await rewrite_profile(
        db, client=client, pasted=payload.pasted, voice_notes=channel.voice_notes, language=payload.language
    )
    panel = (result.get("humanize") or {}).get("panel") or {}
    draft = LinkedInDraft(
        agency_id=user.agency_id,
        channel_id=channel.id,
        kind="profile",
        idea="profile",
        body=result.get("about") or "",
        human_score=panel.get("human_score"),
        verdict=panel.get("verdict") or "",
        payload=result,
    )
    db.add(draft)
    db.commit()
    result["draft_id"] = str(draft.id)
    result["audit"] = result.get("audit") or score_profile_heuristic(payload.pasted)
    return result


@router.post(
    "/channels/{client_id}/drafts/{draft_id}/publish",
    response_model=LinkedInPublicationOut,
)
async def publish_draft(
    client_id: uuid.UUID,
    draft_id: uuid.UUID,
    payload: LinkedInPublishRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not payload.approved:
        raise HTTPException(status_code=400, detail="Explicit approval is required before publishing")
    channel = _get_or_create_channel(db, user, client_id)
    draft = db.scalar(
        select(LinkedInDraft).where(
            LinkedInDraft.id == draft_id,
            LinkedInDraft.channel_id == channel.id,
            LinkedInDraft.agency_id == user.agency_id,
        )
    )
    if not draft or draft.kind != "post":
        raise HTTPException(status_code=404, detail="LinkedIn post draft not found")
    if draft.status == "published" and draft.provider_post_id and draft.published_at:
        return LinkedInPublicationOut(
            draft_id=draft.id,
            status=draft.status,
            provider_post_id=draft.provider_post_id,
            published_at=draft.published_at,
            text=draft.body,
        )
    if not channel.encrypted_access_token or not channel.member_id or channel.status != "connected":
        raise HTTPException(status_code=400, detail="Connect this client's LinkedIn profile before publishing")
    if "w_member_social" not in (channel.granted_scopes or []) and not linkedin_oauth.mock_enabled():
        raise HTTPException(status_code=400, detail="LinkedIn connection is missing w_member_social")
    text = (payload.text if payload.text is not None else draft.body).strip()
    if not text:
        raise HTTPException(status_code=400, detail="LinkedIn post text is empty")
    try:
        provider = LinkedInPublishingProvider(
            member_id=channel.member_id,
            access_token=decrypt_secret(channel.encrypted_access_token),
        )
        post_id = await provider.publish_text(text)
    except LinkedInPublishingError as exc:
        channel.status = "error" if exc.status_code in {401, 403} else channel.status
        channel.last_error = str(exc)
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    draft.body = text
    draft.status = "published"
    draft.provider_post_id = post_id
    draft.published_at = now_utc()
    channel.last_error = None
    db.commit()
    db.refresh(draft)
    return LinkedInPublicationOut(
        draft_id=draft.id,
        status=draft.status,
        provider_post_id=draft.provider_post_id or "",
        published_at=draft.published_at,
        text=draft.body,
    )


@router.get("/channels/{client_id}/drafts", response_model=list[LinkedInDraftOut])
def list_drafts(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    channel = _get_or_create_channel(db, user, client_id)
    rows = db.scalars(
        select(LinkedInDraft).where(LinkedInDraft.channel_id == channel.id).order_by(LinkedInDraft.created_at.desc()).limit(30)
    ).all()
    return rows
