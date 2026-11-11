"""Guided Instagram setup: the same shape as the WhatsApp Meta wizard."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Agency, Client, InstagramChannel, User

router = APIRouter(prefix="/clients/{client_id}/instagram-setup", tags=["Instagram setup"])

REQUIRED = [
    "instagram_basic",
    "instagram_content_publish",
    "instagram_manage_messages",
    "instagram_manage_comments",
    "pages_show_list",
    "pages_manage_posts",
    "business_management",
]


def _step(step_id, title, status, detail, where="", how=None, scope="client"):
    return {
        "id": step_id,
        "title": title,
        "status": status,
        "detail": detail,
        "where": where,
        "how": how or [],
        "scope": scope,
    }


@router.get("")
def get_setup(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = db.get(Client, client_id)
    if client is None or client.agency_id != user.agency_id:
        raise HTTPException(status_code=404, detail="Client not found")
    agency = db.get(Agency, user.agency_id)
    channel = (
        db.query(InstagramChannel)
        .filter(InstagramChannel.client_id == client.id, InstagramChannel.agency_id == user.agency_id)
        .first()
    )

    app_ready = bool(agency and agency.meta_app_id and agency.encrypted_meta_app_secret)
    scopes = set(channel.granted_scopes or []) if channel else set()
    missing = [scope for scope in REQUIRED if scope not in scopes]
    connected = bool(channel and channel.status == "connected")
    page_ready = bool(channel and channel.page_id)
    token_ready = bool(channel and channel.encrypted_access_token)

    steps = [
        _step("app", "App de Meta", "done" if app_ready else "todo",
              "La app es la misma de WhatsApp: se configura una vez por agencia.",
              where="Configuración → Meta",
              how=["Guarda el App ID y el secret de la agencia.", "Este paso se comparte con WhatsApp."],
              scope="agency"),
        _step("permissions", "Permisos de Instagram", "done" if not missing else "todo",
              "Concedidos: " + (", ".join(sorted(scopes)) or "ninguno") if scopes else "Meta no ha concedido permisos todavía.",
              where="Tu app → Casos de uso → Instagram → Permisos",
              how=["Solicita: " + ", ".join(REQUIRED) + ".", "Los permisos de publicación requieren revisión de Meta."],
              scope="agency"),
        _step("connect", "Conectar la cuenta de Instagram", "done" if token_ready else "todo",
              channel.username if channel and channel.username else "Sin cuenta conectada.",
              where="Cliente → Canales → Instagram → Conectar con Instagram",
              how=["El cliente autoriza con su cuenta Business.", "Sin cuenta Business no se puede publicar."]),
        _step("page", "Página de Facebook vinculada", "done" if page_ready else "todo",
              channel.page_id if page_ready else "Instagram exige una Página vinculada.",
              where="Instagram → Configuración → Cuenta vinculada",
              how=["Vincula la cuenta de Instagram a una Página.", "Sin Página, la API de publicación no funciona."]),
        _step("permissions_client", "Permisos sobre esta cuenta", "done" if not missing and token_ready else "todo",
              ("Falta: " + ", ".join(missing)) if missing else "Permisos completos sobre la cuenta.",
              where="Se comprueba sobre el token del cliente"),
        _step("webhook", "Webhook de Instagram", "manual",
              "Se suscribe con los campos messages y comments en la app.",
              where="Tu app → Webhooks → Instagram",
              how=["Suscribe messages para DMs.", "Suscribe comments para comentarios."],
              scope="agency"),
        _step("test", "Publicación de prueba", "done" if connected else "todo",
              "Una imagen real publicada en la cuenta.",
              where="Cliente → Canales → Instagram",
              how=["Publica una imagen desde el panel.", "Comprueba que aparece en el perfil."]),
    ]

    green = sum(1 for step in steps if step["status"] == "done")
    amber = sum(1 for step in steps if step["status"] == "manual")
    red = sum(1 for step in steps if step["status"] == "todo")
    return {
        "steps": steps,
        "summary": {"green": green, "amber": amber, "red": red},
        "can_close": red == 0,
        "channel": {
            "username": channel.username if channel else "",
            "page_id": channel.page_id if channel else "",
            "status": channel.status if channel else "disconnected",
        },
    }
