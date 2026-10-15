import logging
import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Agent, Client, User, WhatsAppCloudChannel, new_public_id, now_utc
from ..schemas_whatsapp_cloud import (
    WhatsAppCloudAgentUpdate,
    WhatsAppCloudChannelOut,
    WhatsAppCloudChannelUpdate,
    WhatsAppCloudHealthOut,
    WhatsAppSignupCompleteOut,
    WhatsAppSignupCompleteRequest,
    WhatsAppSignupOptionsOut,
    WhatsAppSignupSessionIn,
    WhatsAppSignupSessionOut,
    WhatsAppTemplateListOut,
    WhatsAppTemplateSendIn,
    WhatsAppTemplateSendOut,
    WhatsAppWebhookRegistrationOut,
)
from ..security import decrypt_secret, encrypt_secret
from ..services.whatsapp_cloud import list_message_templates, send_template, verify_phone_number
from ..services.legal_consent import record_channel_connect_consent
from ..services.whatsapp_cloud_health import build_health
from ..services.whatsapp_cloud_webhook_register import (
    register_webhook_for_number,
    unregister_webhook_for_number,
)
from ..services.whatsapp_errors import humanize_whatsapp_error
from ..services.whatsapp_meta_signup import (
    build_embedded_signup_url,
    create_signup_state,
    discover_whatsapp_assets,
    exchange_code_for_token,
    parse_signup_state,
    signup_options,
)


logger = logging.getLogger("openlivery.whatsapp_cloud")
router = APIRouter(prefix="/whatsapp-cloud", tags=["WhatsApp Cloud"])


def _channel_for_user(db: Session, user: User, client_id: uuid.UUID) -> WhatsAppCloudChannel:
    channel = db.scalar(
        select(WhatsAppCloudChannel).where(
            WhatsAppCloudChannel.client_id == client_id,
            WhatsAppCloudChannel.agency_id == user.agency_id,
        )
    )
    if not channel:
        raise HTTPException(status_code=404, detail="This client does not have the WhatsApp API configured yet")
    return channel


def _require_client(db: Session, user: User, client_id: uuid.UUID) -> Client:
    client = db.scalar(select(Client).where(Client.id == client_id, Client.agency_id == user.agency_id))
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def _require_agent(db: Session, user: User, client: Client, agent_id: uuid.UUID) -> Agent:
    agent = db.scalar(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.client_id == client.id,
            Agent.agency_id == user.agency_id,
        )
    )
    if not agent:
        raise HTTPException(status_code=400, detail="Select an agent that belongs to this client")
    return agent


def _webhook_url(channel: WhatsAppCloudChannel) -> str:
    return (
        f"{get_settings().frontend_url.rstrip('/')}/api/public/whatsapp-cloud/channels/{channel.id}/webhook"
    )


def _public_channel(channel: WhatsAppCloudChannel, webhook_registration: dict | None = None) -> dict:
    error = humanize_whatsapp_error(channel.last_error) if channel.last_error else None
    return {
        "id": channel.id,
        "client_id": channel.client_id,
        "agent_id": channel.agent_id,
        "status": channel.status,
        "connection_mode": getattr(channel, "connection_mode", None) or "manual",
        "phone_number": channel.phone_number,
        "display_name": channel.display_name,
        "phone_number_id": channel.phone_number_id,
        "waba_id": channel.waba_id,
        "has_access_token": bool(channel.encrypted_access_token),
        "has_app_secret": bool(channel.encrypted_app_secret) or bool(get_settings().meta_app_secret),
        "webhook_url": _webhook_url(channel),
        "webhook_verify_token": channel.webhook_verify_token,
        "last_error": channel.last_error,
        "error_message": error["message"] if error else None,
        "error_code": error["code"] if error else None,
        "is_enabled": channel.is_enabled,
        "last_connected_at": channel.last_connected_at,
        "created_at": channel.created_at,
        "updated_at": channel.updated_at,
        "webhook_registration": webhook_registration,
    }


async def _auto_register_webhook(channel: WhatsAppCloudChannel) -> dict:
    if not channel.encrypted_access_token or not channel.phone_number_id:
        return {
            "ok": False,
            "code": "meta_error",
            "message": "Save access token and phone number ID before registering the webhook",
            "host": None,
            "app_without_webhook": False,
        }
    result = await register_webhook_for_number(
        waba_id=channel.waba_id,
        phone_number_id=channel.phone_number_id,
        access_token=decrypt_secret(channel.encrypted_access_token),
        webhook_url=_webhook_url(channel),
        verify_token=channel.webhook_verify_token,
    )
    return result.as_dict()


def _get_or_create_channel(db: Session, user: User, client: Client, agent: Agent) -> WhatsAppCloudChannel:
    channel = db.scalar(select(WhatsAppCloudChannel).where(WhatsAppCloudChannel.client_id == client.id))
    if channel:
        return channel
    channel = WhatsAppCloudChannel(
        agency_id=user.agency_id,
        client_id=client.id,
        agent_id=agent.id,
        webhook_verify_token=new_public_id(),
        connection_mode="manual",
    )
    db.add(channel)
    db.flush()
    return channel


@router.get("/signup/options", response_model=WhatsAppSignupOptionsOut)
def get_signup_options(user: User = Depends(get_current_user)):
    return signup_options()


@router.get("/channels/{client_id}", response_model=WhatsAppCloudChannelOut)
def get_channel(client_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _public_channel(_channel_for_user(db, user, client_id))


@router.get("/channels/{client_id}/health", response_model=WhatsAppCloudHealthOut)
async def channel_health(client_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    channel = _channel_for_user(db, user, client_id)
    logger.info(
        "whatsapp health check client_id=%s channel_id=%s status=%s phone_number_id=%s",
        client_id,
        channel.id,
        channel.status,
        channel.phone_number_id or "-",
    )
    return await build_health(db, channel)


@router.put("/channels/{client_id}", response_model=WhatsAppCloudChannelOut)
def configure_channel(
    client_id: uuid.UUID,
    payload: WhatsAppCloudChannelUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _require_client(db, user, client_id)
    agent = _require_agent(db, user, client, payload.agent_id)
    channel = _get_or_create_channel(db, user, client, agent)
    channel.agent_id = agent.id
    channel.is_enabled = True
    if payload.phone_number_id is not None:
        channel.phone_number_id = payload.phone_number_id.strip()
    if payload.waba_id is not None:
        channel.waba_id = payload.waba_id.strip() or None
    if payload.connection_mode:
        channel.connection_mode = payload.connection_mode
    elif payload.access_token or payload.app_secret or payload.phone_number_id:
        channel.connection_mode = "manual"
    # Blank secrets keep the stored values, so the form can resubmit safely.
    if payload.access_token:
        channel.encrypted_access_token = encrypt_secret(payload.access_token.strip())
    if payload.app_secret:
        channel.encrypted_app_secret = encrypt_secret(payload.app_secret.strip())
    channel.updated_at = now_utc()
    db.commit()
    db.refresh(channel)
    logger.info(
        "whatsapp channel saved client_id=%s channel_id=%s mode=%s phone_number_id=%s",
        client_id,
        channel.id,
        channel.connection_mode,
        channel.phone_number_id or "-",
    )
    return _public_channel(channel)


@router.patch("/channels/{client_id}/agent", response_model=WhatsAppCloudChannelOut)
def assign_agent(
    client_id: uuid.UUID,
    payload: WhatsAppCloudAgentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _require_client(db, user, client_id)
    agent = _require_agent(db, user, client, payload.agent_id)
    channel = _get_or_create_channel(db, user, client, agent)
    channel.agent_id = agent.id
    channel.updated_at = now_utc()
    db.commit()
    db.refresh(channel)
    return _public_channel(channel)


@router.post("/channels/{client_id}/connect", response_model=WhatsAppCloudChannelOut)
async def connect_channel(client_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    channel = _channel_for_user(db, user, client_id)
    settings = get_settings()
    has_secret = bool(channel.encrypted_app_secret) or bool(settings.meta_app_secret)
    if not channel.encrypted_access_token or not has_secret or not channel.phone_number_id:
        raise HTTPException(
            status_code=400,
            detail="Save the phone number ID, access token and app secret before connecting",
        )
    try:
        profile = await verify_phone_number(
            decrypt_secret(channel.encrypted_access_token), channel.phone_number_id
        )
    except HTTPException as exc:
        channel.status = "error"
        channel.last_error = str(exc.detail)
        channel.updated_at = now_utc()
        db.commit()
        db.refresh(channel)
        return _public_channel(channel)
    channel.status = "connected"
    channel.phone_number = profile.get("display_phone_number")
    channel.display_name = profile.get("verified_name")
    channel.last_error = None
    channel.is_enabled = True
    channel.last_connected_at = now_utc()
    channel.updated_at = now_utc()
    db.commit()
    db.refresh(channel)
    registration = await _auto_register_webhook(channel)
    if not registration.get("ok"):
        # Credentials are valid; surface webhook issues without flipping status to error.
        logger.warning(
            "whatsapp webhook auto-register failed client_id=%s code=%s message=%s",
            client_id,
            registration.get("code"),
            registration.get("message"),
        )
    return _public_channel(channel, webhook_registration=registration)


@router.post("/channels/{client_id}/register-webhook", response_model=WhatsAppWebhookRegistrationOut)
async def register_webhook(client_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Retry Meta webhook override registration without re-pasting credentials."""
    channel = _channel_for_user(db, user, client_id)
    return await _auto_register_webhook(channel)


@router.get("/channels/{client_id}/templates", response_model=WhatsAppTemplateListOut)
async def list_templates(client_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    channel = _channel_for_user(db, user, client_id)
    if not channel.encrypted_access_token or not channel.waba_id:
        raise HTTPException(status_code=400, detail="Save access token and WABA ID before listing templates")
    raw = await list_message_templates(decrypt_secret(channel.encrypted_access_token), channel.waba_id)
    templates = [
        {
            "id": item.get("id"),
            "name": item.get("name") or "",
            "language": item.get("language"),
            "status": item.get("status"),
            "category": item.get("category"),
            "components": item.get("components") or [],
        }
        for item in raw
        if item.get("name")
    ]
    return {"templates": templates, "count": len(templates)}


@router.post("/channels/{client_id}/templates/send", response_model=WhatsAppTemplateSendOut)
async def send_channel_template(
    client_id: uuid.UUID,
    payload: WhatsAppTemplateSendIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    channel = _channel_for_user(db, user, client_id)
    if not channel.encrypted_access_token or not channel.phone_number_id:
        raise HTTPException(status_code=400, detail="Save access token and phone number ID before sending templates")
    if channel.status != "connected" or not channel.is_enabled:
        raise HTTPException(status_code=400, detail="Connect the WhatsApp Cloud channel before sending templates")
    wamid = await send_template(
        decrypt_secret(channel.encrypted_access_token),
        channel.phone_number_id,
        payload.to.strip(),
        name=payload.name.strip(),
        language=payload.language.strip(),
        body_parameters=payload.body_parameters,
    )
    return {
        "wamid": wamid,
        "to": payload.to.strip(),
        "name": payload.name.strip(),
        "language": payload.language.strip(),
    }


@router.post("/channels/{client_id}/test", response_model=WhatsAppCloudHealthOut)
async def test_channel(client_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Run connect verification (if possible) then return health."""
    channel = _channel_for_user(db, user, client_id)
    if channel.encrypted_access_token and channel.phone_number_id:
        try:
            profile = await verify_phone_number(
                decrypt_secret(channel.encrypted_access_token), channel.phone_number_id
            )
            channel.status = "connected"
            channel.phone_number = profile.get("display_phone_number")
            channel.display_name = profile.get("verified_name")
            channel.last_error = None
            channel.is_enabled = True
            channel.last_connected_at = now_utc()
        except HTTPException as exc:
            channel.status = "error"
            channel.last_error = str(exc.detail)
        channel.updated_at = now_utc()
        db.commit()
        db.refresh(channel)
    return await build_health(db, channel)


@router.post("/channels/{client_id}/disconnect", response_model=WhatsAppCloudChannelOut)
async def disconnect_channel(client_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    channel = _channel_for_user(db, user, client_id)
    if channel.encrypted_access_token and channel.phone_number_id:
        path = urlparse(_webhook_url(channel)).path
        try:
            await unregister_webhook_for_number(
                phone_number_id=channel.phone_number_id,
                access_token=decrypt_secret(channel.encrypted_access_token),
                webhook_path=path,
            )
        except Exception:  # noqa: BLE001 — disconnect must succeed locally
            logger.warning("whatsapp webhook unregister failed client_id=%s", client_id, exc_info=True)
    channel.status = "disconnected"
    channel.is_enabled = False
    channel.last_error = None
    channel.updated_at = now_utc()
    db.commit()
    db.refresh(channel)
    logger.info("whatsapp channel disconnected client_id=%s channel_id=%s", client_id, channel.id)
    return _public_channel(channel)


@router.post("/channels/{client_id}/signup/session", response_model=WhatsAppSignupSessionOut)
def start_signup_session(
    client_id: uuid.UUID,
    payload: WhatsAppSignupSessionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_client(db, user, client_id)
    if payload.consent.client_id != client_id:
        raise HTTPException(status_code=400, detail="Consent client mismatch")
    record_channel_connect_consent(db, user=user, payload=payload.consent)
    options = signup_options()
    settings = get_settings()
    state = create_signup_state(
        agency_id=str(user.agency_id),
        client_id=str(client_id),
        user_id=str(user.id),
    )
    return {
        "state": state,
        "meta_app_id": settings.meta_app_id or None,
        "meta_config_id": settings.meta_whatsapp_config_id or None,
        "mock_mode": settings.meta_mock_mode,
        "redirect_url": build_embedded_signup_url(state),
        "blocked_reason": options.get("blocked_reason"),
    }


@router.post("/channels/{client_id}/signup/complete", response_model=WhatsAppSignupCompleteOut)
async def complete_signup(
    client_id: uuid.UUID,
    payload: WhatsAppSignupCompleteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = _require_client(db, user, client_id)
    state = parse_signup_state(payload.state)
    if state["client_id"] != str(client_id) or state["agency_id"] != str(user.agency_id) or state["user_id"] != str(user.id):
        raise HTTPException(status_code=403, detail="OAuth state does not match this client")

    settings = get_settings()
    use_mock = payload.use_mock or settings.meta_mock_mode
    if not use_mock and not payload.code and not (payload.phone_number_id and payload.waba_id):
        raise HTTPException(status_code=400, detail="Authorization code or WhatsApp assets are required")

    agent_id = payload.agent_id
    if agent_id is None:
        existing = db.scalar(select(WhatsAppCloudChannel).where(WhatsAppCloudChannel.client_id == client.id))
        if existing:
            agent_id = existing.agent_id
        else:
            first = db.scalar(select(Agent).where(Agent.client_id == client.id).order_by(Agent.created_at.asc()))
            agent_id = first.id if first else None
    if agent_id is None:
        raise HTTPException(status_code=400, detail="Assign an agent before connecting WhatsApp")
    agent = _require_agent(db, user, client, agent_id)

    if use_mock:
        access_token = "mock-access-token"
        assets = await discover_whatsapp_assets(access_token)
    else:
        access_token = await exchange_code_for_token(payload.code or "")
        assets = await discover_whatsapp_assets(access_token)
        if payload.phone_number_id:
            assets["phone_number_id"] = payload.phone_number_id
        if payload.waba_id:
            assets["waba_id"] = payload.waba_id

    channel = _get_or_create_channel(db, user, client, agent)
    channel.agent_id = agent.id
    channel.connection_mode = "embedded" if not use_mock else "managed"
    channel.phone_number_id = assets["phone_number_id"]
    channel.waba_id = assets.get("waba_id")
    channel.phone_number = assets.get("phone_number")
    channel.display_name = assets.get("display_name")
    channel.encrypted_access_token = encrypt_secret(access_token)
    if settings.meta_app_secret and not channel.encrypted_app_secret:
        # Platform secret is used at webhook time; no need to duplicate into channel
        # unless BYO mode later overwrites.
        pass
    channel.status = "connected"
    channel.is_enabled = True
    channel.last_error = None
    channel.last_connected_at = now_utc()
    channel.updated_at = now_utc()
    steps = assets.get("steps") or []
    for step in steps:
        if step["id"] in {"credentials", "webhook"}:
            step["done"] = True
    db.commit()
    db.refresh(channel)
    registration = await _auto_register_webhook(channel)
    if registration.get("ok"):
        for step in steps:
            if step.get("id") == "webhook":
                step["done"] = True
                step["detail"] = registration.get("message")
    else:
        for step in steps:
            if step.get("id") == "webhook":
                step["done"] = False
                step["detail"] = registration.get("message")
    logger.info(
        "whatsapp signup complete client_id=%s channel_id=%s mode=%s phone_number_id=%s webhook=%s",
        client_id,
        channel.id,
        channel.connection_mode,
        channel.phone_number_id,
        registration.get("code"),
    )
    return {"channel": _public_channel(channel, webhook_registration=registration), "steps": steps}


@router.get("/oauth/callback")
async def oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    """Browser landing after Meta OAuth; redirects into the client WhatsApp page."""
    settings = get_settings()
    if error or not state:
        target = f"{settings.frontend_url.rstrip('/')}/clients?whatsapp_oauth=error"
        if error_description:
            target += f"&detail={error_description[:120]}"
        return RedirectResponse(target)
    try:
        parsed = parse_signup_state(state)
        client_id = parsed["client_id"]
    except HTTPException:
        return RedirectResponse(f"{settings.frontend_url.rstrip('/')}/clients?whatsapp_oauth=error")
    redirect = (
        f"{settings.frontend_url.rstrip('/')}/clients/{client_id}/channels/whatsapp-cloud"
        f"?oauth_code={code or ''}&oauth_state={state}"
    )
    return RedirectResponse(redirect)
