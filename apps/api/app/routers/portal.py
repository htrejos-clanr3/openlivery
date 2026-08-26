import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from ..config import get_settings
from ..database import get_db
from ..models import (
    Agency,
    Agent,
    Carousel,
    CarouselEvent,
    Client,
    Conversation,
    Message,
    OAuthAccount,
    PortalUser,
    now_utc,
)
from ..ratelimit import login_rate_limit
from ..schemas import (
    AgentSummary,
    AuthOptionsOut,
    CarouselOut,
    CarouselSlideDecision,
    CarouselSlideOut,
    ConversationDetail,
    ConversationModeUpdate,
    ConversationOut,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    GoogleAuthRequest,
    PortalLoginRequest,
    PortalPublicOut,
    PortalSessionOut,
    ResetPasswordRequest,
    SendMessageRequest,
    SetPasswordRequest,
)
from ..security import create_portal_token, decode_portal_token, hash_password, verify_password
from ..services.auth_identity import (
    consume_password_token,
    generic_forgot_message,
    issue_password_token,
    link_or_get_oauth,
    verify_google_id_token,
)
from ..services.whatsapp import send_channel_message


router = APIRouter(prefix="/portal", tags=["Client portal"])


def _public_client(db: Session, slug: str) -> Client:
    client = db.scalar(select(Client).where(Client.portal_slug == slug, Client.portal_enabled.is_(True)))
    if not client:
        raise HTTPException(status_code=404, detail="Portal not found or disabled")
    return client


class PortalAuth:
    def __init__(self, client: Client, portal_user: PortalUser | None):
        self.client = client
        self.portal_user = portal_user


def _portal_auth(
    slug: str,
    portal_access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> PortalAuth:
    if not portal_access_token:
        raise HTTPException(status_code=401, detail="Sign in to the portal")
    payload = decode_portal_token(portal_access_token)
    if not payload or payload.get("portal_slug") != slug:
        raise HTTPException(status_code=401, detail="The portal session expired")
    try:
        client_id = uuid.UUID(payload["sub"])
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid portal session") from exc
    client = db.scalar(
        select(Client).where(Client.id == client_id, Client.portal_slug == slug, Client.portal_enabled.is_(True))
    )
    if not client:
        raise HTTPException(status_code=401, detail="The portal is no longer available")
    portal_user = None
    raw_uid = payload.get("portal_user_id")
    if raw_uid:
        try:
            portal_user = db.get(PortalUser, uuid.UUID(str(raw_uid)))
        except ValueError:
            portal_user = None
        if portal_user and (portal_user.client_id != client.id or not portal_user.is_active):
            raise HTTPException(status_code=401, detail="The portal session expired")
    return PortalAuth(client=client, portal_user=portal_user)


def _portal_client(
    slug: str,
    portal_access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> Client:
    return _portal_auth(slug, portal_access_token, db).client


def _session_out(db: Session, client: Client, portal_user: PortalUser | None = None) -> dict:
    agency = db.get(Agency, client.agency_id)
    return {
        "client_id": client.id,
        "client_name": client.name,
        "portal_slug": client.portal_slug,
        "agency_name": agency.name,
        "portal_user_id": portal_user.id if portal_user else None,
        "portal_user_name": portal_user.name if portal_user else None,
        "portal_user_email": portal_user.email if portal_user else None,
        "password_configured": portal_user.password_configured if portal_user else bool(client.portal_password_hash),
    }


def _set_portal_cookie(response: Response, client: Client, portal_user: PortalUser | None = None) -> None:
    settings = get_settings()
    response.set_cookie(
        key="portal_access_token",
        value=create_portal_token(
            str(client.id),
            client.portal_slug,
            str(portal_user.id) if portal_user else None,
        ),
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_minutes * 60,
        path="/",
    )


def _detail(db: Session, client: Client, conversation_id: uuid.UUID) -> Conversation:
    conversation = db.scalar(
        select(Conversation)
        .options(selectinload(Conversation.messages), joinedload(Conversation.agent))
        .execution_options(populate_existing=True)
        .where(Conversation.id == conversation_id, Conversation.client_id == client.id)
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


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
        slides=[CarouselSlideOut.model_validate(s) for s in sorted(carousel.slides, key=lambda x: x.position)],
    )


@router.get("/{slug}", response_model=PortalPublicOut)
def public_portal(slug: str, db: Session = Depends(get_db)):
    client = _public_client(db, slug)
    agency = db.get(Agency, client.agency_id)
    return {
        "client_name": client.name,
        "portal_title": client.portal_title or f"{client.name} Inbox",
        "portal_slug": client.portal_slug,
        "agency_name": agency.name,
        "agency_brand_color": agency.brand_color,
        "agency_logo_url": f"/api/portal/{slug}/logo" if agency.logo_data else None,
    }


@router.get("/{slug}/auth-options", response_model=AuthOptionsOut)
def portal_auth_options(slug: str, db: Session = Depends(get_db)):
    _public_client(db, slug)
    settings = get_settings()
    client_id = settings.google_oauth_client_id.strip() or None
    return AuthOptionsOut(google_enabled=bool(client_id), google_client_id=client_id)


@router.get("/{slug}/logo")
def public_logo(slug: str, db: Session = Depends(get_db)):
    client = _public_client(db, slug)
    agency = db.get(Agency, client.agency_id)
    if not agency.logo_data or not agency.logo_mime:
        raise HTTPException(status_code=404, detail="Logo not found")
    return Response(content=agency.logo_data, media_type=agency.logo_mime, headers={"Cache-Control": "no-store"})


@router.post("/{slug}/login", response_model=PortalSessionOut, dependencies=[Depends(login_rate_limit)])
def portal_login(slug: str, payload: PortalLoginRequest, response: Response, db: Session = Depends(get_db)):
    client = _public_client(db, slug)
    email = payload.email.lower()
    portal_user = db.scalar(
        select(PortalUser).where(
            PortalUser.client_id == client.id,
            PortalUser.email == email,
            PortalUser.is_active.is_(True),
        )
    )
    if portal_user and portal_user.password_hash and verify_password(payload.password, portal_user.password_hash):
        _set_portal_cookie(response, client, portal_user)
        return _session_out(db, client, portal_user)

    if (
        client.portal_email
        and email == client.portal_email.lower()
        and client.portal_password_hash
        and verify_password(payload.password, client.portal_password_hash)
    ):
        _set_portal_cookie(response, client, None)
        return _session_out(db, client, None)

    raise HTTPException(status_code=401, detail="Incorrect email or password")


@router.post("/{slug}/google", response_model=PortalSessionOut, dependencies=[Depends(login_rate_limit)])
def portal_google(slug: str, payload: GoogleAuthRequest, response: Response, db: Session = Depends(get_db)):
    client = _public_client(db, slug)
    identity = verify_google_id_token(payload.id_token)
    oauth = db.scalar(
        select(OAuthAccount).where(OAuthAccount.provider == "google", OAuthAccount.subject == identity.subject)
    )
    portal_user: PortalUser | None = None
    if oauth and oauth.portal_user_id:
        portal_user = db.get(PortalUser, oauth.portal_user_id)
        if portal_user and portal_user.client_id != client.id:
            raise HTTPException(status_code=403, detail="Google account is linked to another portal")
    if not portal_user:
        portal_user = db.scalar(
            select(PortalUser).where(PortalUser.client_id == client.id, PortalUser.email == identity.email)
        )
    if not portal_user:
        raise HTTPException(
            status_code=403,
            detail="No registered portal user for this Google account. Ask the agency to invite your email.",
        )
    if not portal_user.is_active:
        raise HTTPException(status_code=403, detail="Portal user is inactive")
    link_or_get_oauth(db, identity=identity, portal_user=portal_user)
    db.commit()
    _set_portal_cookie(response, client, portal_user)
    return _session_out(db, client, portal_user)


@router.post("/{slug}/forgot-password", response_model=ForgotPasswordResponse, dependencies=[Depends(login_rate_limit)])
def portal_forgot_password(slug: str, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    client = _public_client(db, slug)
    settings = get_settings()
    message = generic_forgot_message()
    email = payload.email.lower()
    portal_user = db.scalar(select(PortalUser).where(PortalUser.client_id == client.id, PortalUser.email == email))
    if not portal_user:
        return ForgotPasswordResponse(message=message)

    has_google = bool(
        db.scalar(
            select(OAuthAccount).where(OAuthAccount.portal_user_id == portal_user.id, OAuthAccount.provider == "google")
        )
    )
    if not portal_user.password_hash and has_google:
        raw = issue_password_token(db, email=email, audience="portal", purpose="set", portal_user=portal_user)
        db.commit()
        return ForgotPasswordResponse(
            message=message,
            account_kind="google_only",
            reset_token=raw if settings.auth_expose_reset_token else None,
        )
    if not portal_user.password_hash:
        return ForgotPasswordResponse(message=message)
    raw = issue_password_token(db, email=email, audience="portal", purpose="reset", portal_user=portal_user)
    db.commit()
    return ForgotPasswordResponse(
        message=message,
        account_kind="reset_sent",
        reset_token=raw if settings.auth_expose_reset_token else None,
    )


@router.post("/{slug}/reset-password", response_model=PortalSessionOut)
def portal_reset_password(slug: str, payload: ResetPasswordRequest, response: Response, db: Session = Depends(get_db)):
    client = _public_client(db, slug)
    row = consume_password_token(db, payload.token, purpose="reset")
    if row.audience != "portal" or not row.portal_user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    portal_user = db.get(PortalUser, row.portal_user_id)
    if not portal_user or portal_user.client_id != client.id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    portal_user.password_hash = hash_password(payload.password)
    db.commit()
    _set_portal_cookie(response, client, portal_user)
    return _session_out(db, client, portal_user)


@router.post("/{slug}/set-password", response_model=PortalSessionOut)
def portal_set_password(slug: str, payload: SetPasswordRequest, response: Response, db: Session = Depends(get_db)):
    client = _public_client(db, slug)
    row = consume_password_token(db, payload.token, purpose="set")
    if row.audience != "portal" or not row.portal_user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    portal_user = db.get(PortalUser, row.portal_user_id)
    if not portal_user or portal_user.client_id != client.id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    portal_user.password_hash = hash_password(payload.password)
    db.commit()
    _set_portal_cookie(response, client, portal_user)
    return _session_out(db, client, portal_user)


@router.post("/{slug}/logout", status_code=status.HTTP_204_NO_CONTENT)
def portal_logout(response: Response):
    response.delete_cookie("portal_access_token", path="/")


@router.get("/{slug}/me", response_model=PortalSessionOut)
def portal_me(slug: str, auth: PortalAuth = Depends(_portal_auth), db: Session = Depends(get_db)):
    return _session_out(db, auth.client, auth.portal_user)


@router.get("/{slug}/carousels", response_model=list[CarouselOut])
def portal_carousels(slug: str, auth: PortalAuth = Depends(_portal_auth), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Carousel)
        .options(selectinload(Carousel.slides))
        .where(
            Carousel.client_id == auth.client.id,
            Carousel.status.in_(["in_review", "approved", "rejected", "scheduled", "published"]),
        )
        .order_by(Carousel.updated_at.desc())
    ).all()
    return [_carousel_out(row) for row in rows]


@router.get("/{slug}/carousels/{carousel_id}", response_model=CarouselOut)
def portal_carousel(
    slug: str, carousel_id: uuid.UUID, auth: PortalAuth = Depends(_portal_auth), db: Session = Depends(get_db)
):
    carousel = db.scalar(
        select(Carousel)
        .options(selectinload(Carousel.slides))
        .where(Carousel.id == carousel_id, Carousel.client_id == auth.client.id)
    )
    if not carousel:
        raise HTTPException(status_code=404, detail="Carousel not found")
    return _carousel_out(carousel)


@router.post("/{slug}/carousels/{carousel_id}/slides/{slide_id}/approve", response_model=CarouselSlideOut)
def portal_approve_slide(
    slug: str,
    carousel_id: uuid.UUID,
    slide_id: uuid.UUID,
    auth: PortalAuth = Depends(_portal_auth),
    db: Session = Depends(get_db),
):
    if not auth.portal_user:
        raise HTTPException(status_code=403, detail="A registered portal user is required to approve")
    carousel = db.scalar(
        select(Carousel)
        .options(selectinload(Carousel.slides))
        .where(Carousel.id == carousel_id, Carousel.client_id == auth.client.id, Carousel.status == "in_review")
    )
    if not carousel:
        raise HTTPException(status_code=404, detail="Carousel not found or not in review")
    slide = next((s for s in carousel.slides if s.id == slide_id), None)
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    slide.client_status = "client_ok"
    db.add(
        CarouselEvent(
            carousel_id=carousel.id,
            actor_type="portal",
            actor_id=auth.portal_user.id,
            action="client_approve_slide",
            payload={"slide_id": str(slide_id)},
        )
    )
    db.commit()
    db.refresh(slide)
    return CarouselSlideOut.model_validate(slide)


@router.post("/{slug}/carousels/{carousel_id}/slides/{slide_id}/reject", response_model=CarouselSlideOut)
def portal_reject_slide(
    slug: str,
    carousel_id: uuid.UUID,
    slide_id: uuid.UUID,
    payload: CarouselSlideDecision | None = None,
    auth: PortalAuth = Depends(_portal_auth),
    db: Session = Depends(get_db),
):
    if not auth.portal_user:
        raise HTTPException(status_code=403, detail="A registered portal user is required to reject")
    carousel = db.scalar(
        select(Carousel)
        .options(selectinload(Carousel.slides))
        .where(Carousel.id == carousel_id, Carousel.client_id == auth.client.id, Carousel.status == "in_review")
    )
    if not carousel:
        raise HTTPException(status_code=404, detail="Carousel not found or not in review")
    slide = next((s for s in carousel.slides if s.id == slide_id), None)
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    slide.client_status = "rejected"
    if payload and payload.comment:
        slide.client_comment = payload.comment
    db.add(
        CarouselEvent(
            carousel_id=carousel.id,
            actor_type="portal",
            actor_id=auth.portal_user.id,
            action="client_reject_slide",
            payload={"slide_id": str(slide_id)},
        )
    )
    db.commit()
    db.refresh(slide)
    return CarouselSlideOut.model_validate(slide)


@router.post("/{slug}/carousels/{carousel_id}/approve-set", response_model=CarouselOut)
def portal_approve_set(
    slug: str, carousel_id: uuid.UUID, auth: PortalAuth = Depends(_portal_auth), db: Session = Depends(get_db)
):
    if not auth.portal_user:
        raise HTTPException(status_code=403, detail="A registered portal user is required to approve")
    carousel = db.scalar(
        select(Carousel)
        .options(selectinload(Carousel.slides))
        .where(Carousel.id == carousel_id, Carousel.client_id == auth.client.id, Carousel.status == "in_review")
    )
    if not carousel:
        raise HTTPException(status_code=404, detail="Carousel not found or not in review")
    if any(s.client_status != "client_ok" for s in carousel.slides):
        raise HTTPException(status_code=400, detail="Approve every slide before approving the set")
    carousel.status = "approved"
    carousel.approved_by_portal_user_id = auth.portal_user.id
    carousel.updated_at = now_utc()
    db.add(
        CarouselEvent(
            carousel_id=carousel.id,
            actor_type="portal",
            actor_id=auth.portal_user.id,
            action="client_approve_set",
            payload={},
        )
    )
    db.commit()
    return _carousel_out(carousel)


@router.post("/{slug}/carousels/{carousel_id}/reject-set", response_model=CarouselOut)
def portal_reject_set(
    slug: str,
    carousel_id: uuid.UUID,
    payload: CarouselSlideDecision | None = None,
    auth: PortalAuth = Depends(_portal_auth),
    db: Session = Depends(get_db),
):
    if not auth.portal_user:
        raise HTTPException(status_code=403, detail="A registered portal user is required to reject")
    carousel = db.scalar(
        select(Carousel)
        .options(selectinload(Carousel.slides))
        .where(Carousel.id == carousel_id, Carousel.client_id == auth.client.id, Carousel.status == "in_review")
    )
    if not carousel:
        raise HTTPException(status_code=404, detail="Carousel not found or not in review")
    carousel.status = "rejected"
    carousel.updated_at = now_utc()
    db.add(
        CarouselEvent(
            carousel_id=carousel.id,
            actor_type="portal",
            actor_id=auth.portal_user.id,
            action="client_reject_set",
            payload={"comment": payload.comment if payload else None},
        )
    )
    db.commit()
    return _carousel_out(carousel)


@router.get("/{slug}/agents", response_model=list[AgentSummary])
def portal_agents(slug: str, client: Client = Depends(_portal_client), db: Session = Depends(get_db)):
    return db.scalars(select(Agent).where(Agent.client_id == client.id).order_by(Agent.name)).all()


@router.get("/{slug}/conversations", response_model=list[ConversationOut])
def portal_conversations(slug: str, client: Client = Depends(_portal_client), db: Session = Depends(get_db)):
    ranked = select(
        Message.conversation_id.label("cid"),
        Message.content.label("content"),
        func.row_number().over(partition_by=Message.conversation_id, order_by=Message.created_at.desc()).label("rn"),
    ).subquery()
    last = select(ranked).where(ranked.c.rn == 1).subquery()
    rows = db.execute(
        select(Conversation, last.c.content)
        .outerjoin(last, last.c.cid == Conversation.id)
        .where(Conversation.client_id == client.id)
        .order_by(Conversation.updated_at.desc())
    ).all()
    return [
        ConversationOut.model_validate(conv).model_copy(update={"preview": (content or "")[:140].strip()})
        for conv, content in rows
    ]


@router.get("/{slug}/conversations/{conversation_id}", response_model=ConversationDetail)
def portal_conversation(
    slug: str, conversation_id: uuid.UUID, client: Client = Depends(_portal_client), db: Session = Depends(get_db)
):
    return _detail(db, client, conversation_id)


@router.patch("/{slug}/conversations/{conversation_id}/mode", response_model=ConversationDetail)
def portal_mode(
    slug: str,
    conversation_id: uuid.UUID,
    payload: ConversationModeUpdate,
    client: Client = Depends(_portal_client),
    db: Session = Depends(get_db),
):
    conversation = _detail(db, client, conversation_id)
    conversation.mode = payload.mode
    conversation.updated_at = now_utc()
    db.commit()
    return _detail(db, client, conversation_id)


@router.post("/{slug}/conversations/{conversation_id}/reply", response_model=ConversationDetail)
async def portal_reply(
    slug: str,
    conversation_id: uuid.UUID,
    payload: SendMessageRequest,
    client: Client = Depends(_portal_client),
    db: Session = Depends(get_db),
):
    conversation = _detail(db, client, conversation_id)
    if conversation.mode != "human":
        raise HTTPException(status_code=409, detail="Take control of the conversation before replying")
    external_message_id = await send_channel_message(db, conversation, payload.content.strip())
    db.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=payload.content.strip(),
            sender_type="human",
            sender_name=client.name,
            external_message_id=external_message_id,
        )
    )
    conversation.updated_at = now_utc()
    db.commit()
    return _detail(db, client, conversation_id)
