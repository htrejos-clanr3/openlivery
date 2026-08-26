"""Connection health diagnostics for WhatsApp Cloud channels."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Conversation, Message, WhatsAppCloudChannel
from ..security import decrypt_secret
from .whatsapp_cloud import verify_phone_number
from .whatsapp_errors import humanize_whatsapp_error


def _iso(value: datetime | None) -> str | None:
    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


async def build_health(db: Session, channel: WhatsAppCloudChannel) -> dict:
    settings = get_settings()
    token_configured = bool(channel.encrypted_access_token)
    app_secret_configured = bool(channel.encrypted_app_secret) or bool(settings.meta_app_secret)
    phone_configured = bool(channel.phone_number_id and channel.phone_number_id.strip())
    agent_assigned = bool(channel.agent_id)
    webhook_configured = bool(channel.webhook_verify_token)

    permissions_valid = False
    graph_ok = False
    phone_number = channel.phone_number
    display_name = channel.display_name
    error_info = None

    if token_configured and phone_configured:
        try:
            profile = await verify_phone_number(
                decrypt_secret(channel.encrypted_access_token),
                channel.phone_number_id,
            )
            graph_ok = True
            permissions_valid = True
            phone_number = profile.get("display_phone_number") or phone_number
            display_name = profile.get("verified_name") or display_name
        except Exception as exc:  # noqa: BLE001 — surface as health status
            detail = getattr(exc, "detail", None) or str(exc)
            error_info = humanize_whatsapp_error(str(detail))

    last_inbound = db.scalar(
        select(func.max(Message.created_at))
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Conversation.whatsapp_cloud_channel_id == channel.id,
            Message.role == "user",
        )
    )
    last_outbound = db.scalar(
        select(func.max(Message.created_at))
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Conversation.whatsapp_cloud_channel_id == channel.id,
            Message.role == "assistant",
        )
    )

    connected = (
        channel.status == "connected"
        and channel.is_enabled
        and token_configured
        and phone_configured
        and graph_ok
    )

    if connected:
        ui_status = "connected"
    elif channel.status == "error" or error_info:
        ui_status = "needs_attention"
    elif channel.status == "disconnected" and not token_configured:
        ui_status = "not_configured"
    elif token_configured and not graph_ok:
        ui_status = "needs_attention"
    else:
        ui_status = "disconnected"

    return {
        "connected": connected,
        "ui_status": ui_status,
        "connection_mode": getattr(channel, "connection_mode", None) or "manual",
        "status": channel.status,
        "phone_number": phone_number,
        "display_name": display_name,
        "phone_number_id": channel.phone_number_id or None,
        "waba_id": channel.waba_id,
        "waba_configured": bool(channel.waba_id),
        "token_configured": token_configured,
        "app_secret_configured": app_secret_configured,
        "permissions_valid": permissions_valid,
        "webhook_configured": webhook_configured,
        "agent_assigned": agent_assigned,
        "is_enabled": channel.is_enabled,
        "graph_reachable": graph_ok,
        "last_inbound_message_at": _iso(last_inbound),
        "last_outbound_message_at": _iso(last_outbound),
        "last_connected_at": _iso(channel.last_connected_at),
        "last_error": channel.last_error,
        "error": error_info,
    }
