"""Guided Meta setup status for one client.

The wizard shows ten steps. Everything that can be derived from stored state is
computed here; the two Graph probes are best-effort and degrade to "unknown"
instead of failing the page.
"""

from __future__ import annotations

import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Agency, Client, User, WhatsAppCloudChannel

router = APIRouter(prefix="/clients/{client_id}/meta-setup", tags=["Meta setup"])
REQUIRED_SCOPES = {"whatsapp_business_messaging", "whatsapp_business_management"}


def _channel(db: Session, user: User, client_id: uuid.UUID) -> tuple[Client, WhatsAppCloudChannel | None]:
    client = db.scalar(select(Client).where(Client.id == client_id, Client.agency_id == user.agency_id))
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    channel = db.scalar(select(WhatsAppCloudChannel).where(WhatsAppCloudChannel.client_id == client.id))
    return client, channel


def _graph(path: str, token: str, *, params: dict | None = None) -> dict | None:
    base = get_settings().meta_graph_base_url.rstrip("/")
    try:
        with httpx.Client(timeout=8) as client:
            response = client.get(f"{base}/{path}", params=params or {}, headers={"Authorization": f"Bearer {token}"})
        payload = response.json()
        return payload if isinstance(payload, dict) else None
    except Exception:  # noqa: BLE001 — a probe must never break the page
        return None


def _step(step_id: str, title: str, status: str, detail: str, link: str = "", value: str = "",
          where: str = "", how: list[str] | None = None) -> dict:
    return {"id": step_id, "title": title, "status": status, "detail": detail, "link": link,
            "value": value, "where": where, "how": how or []}


@router.get("")
def meta_setup(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    client, channel = _channel(db, user, client_id)
    public = settings.frontend_url.rstrip("/")
    callback = ""
    verify = ""
    if channel:
        callback = f"{public}/api/public/whatsapp-cloud/channels/{channel.id}/webhook"
        verify = channel.webhook_verify_token or ""

    steps: list[dict] = []
    has_credentials = bool(channel and channel.phone_number_id and channel.waba_id)
    has_token = bool(channel and channel.encrypted_access_token)
    agency_row = db.get(Agency, user.agency_id)
    app_registered = bool(agency_row and agency_row.meta_app_id)
    steps.append(_step("app", "App de Meta", "done" if app_registered else "todo",
        "Crea la app una vez por agencia y registra su App ID en el paso 2.",
        "https://developers.facebook.com/apps",
        where="developers.facebook.com/apps → Crear app → Nombre y correo → Siguiente → Casos de uso",
        how=["Elige el caso de uso «Conéctate con los clientes a través de WhatsApp».",
             "Si ya la creaste, ábrela en «Mis apps».",
             "Registra su App ID y su secret en el paso 2: hasta entonces este paso no puede ponerse verde."]))
    agency = db.get(Agency, user.agency_id)
    has_app = bool(agency and agency.meta_app_id and agency.encrypted_meta_app_secret)
    steps.append(_step("credentials", "App ID y secret",
        "done" if has_app else "todo",
        "Sin estos dos datos no se puede validar nada.",
        where="Tu app → Configuración de la app → Básica",
        how=["Copia «Identificador de la app».",
             "Pulsa «Mostrar» en «Clave secreta» y cópiala.",
             "Pega ambos en Configuración → Meta: se guardan una vez para toda la agencia."]))
    steps.append(_step("waba", "WABA y número", "done" if has_credentials else "todo",
        f"Phone number ID {channel.phone_number_id}" if has_credentials else "Los dos identificadores del número y de la cuenta.",
        where="Tu app → WhatsApp → Configuración de la API",
        how=["Si no ves «WhatsApp» en el menú izquierdo, ve a Panel → Productos → WhatsApp → Configurar.",
             "Copia «Identificador del número de teléfono».",
             "Copia «Identificador de la cuenta de WhatsApp Business».",
             "Pégalos en Configuración avanzada del canal y guarda."]))
    steps.append(_step("token", "Token del system user", "done" if has_token else "todo",
        "El token temporal dura 24 horas: sirve para probar, no para operar.",
        where="business.facebook.com → Configuración del negocio → Usuarios → Usuarios del sistema",
        how=["Crea un usuario del sistema y asígnale la app y la WABA.",
             "Genera el token con whatsapp_business_messaging y whatsapp_business_management.",
             "Pega el token en Configuración avanzada del canal."]))

    if channel and has_token:
        from .. import security as security_module
        decrypt = (getattr(security_module, "decrypt_secret", None)
                   or getattr(security_module, "decrypt_text", None)
                   or getattr(security_module, "decrypt", None))
        token = decrypt(channel.encrypted_access_token) if decrypt and channel.encrypted_access_token else None
        webhook_status, webhook_detail = "unknown", "No se pudo comprobar contra Meta."
        scopes_status, scopes_detail = "unknown", "No se pudieron leer los permisos concedidos."
        if token:
            info = _graph(f"{channel.phone_number_id}", token, params={"fields": "webhook_configuration"})
            if isinstance(info, dict):
                config = info.get("webhook_configuration") or {}
                actual = config.get("phone_number") if isinstance(config, dict) else None
                webhook_status = "done" if actual and actual.rstrip("/") == callback.rstrip("/") else "todo"
                webhook_detail = "Meta confirma la URL en el número." if webhook_status == "done" else "Meta no tiene registrada esta URL en el número."
            debug = _graph("debug_token", token, params={"input_token": token})
            data = (debug or {}).get("data") or {}
            granted = set(data.get("scopes") or [])
            if granted:
                missing = sorted(REQUIRED_SCOPES - granted)
                scopes_status = "todo" if missing else "done"
                scopes_detail = f"Falta {', '.join(missing)}" if missing else "Permisos completos."
        steps.append(_step("webhook", "Webhook registrado", webhook_status, webhook_detail, value=callback,
            where="Tu app → WhatsApp → Configuración → Webhook → Editar",
            how=["El menú WhatsApp solo existe si agregaste el producto; si no está, completa el paso 3.",
                 "Pega la URL de callback y el token de verificación de abajo.",
                 "Pulsa «Verificar y guardar».",
                 "Suscribe el campo messages."]))
        steps.append(_step("scopes", "Permisos concedidos", scopes_status, scopes_detail,
            where="Se comprueba sobre el token, no en una pantalla de Meta",
            how=["Si falta un permiso, edita el usuario del sistema y genera un token nuevo.",
                 "El token anterior no hereda permisos."]))
    else:
        steps.append(_step("webhook", "Webhook registrado", "todo", "Se registra cuando exista un token.", value=callback,
            where="Tu app → WhatsApp → Configuración → Webhook → Editar",
            how=["Primero completa los pasos 2 a 4 (incluido agregar el producto WhatsApp).",
                 "Después pega la URL de callback y el token de verificación."]))
        steps.append(_step("scopes", "Permisos concedidos", "todo", "Se comprueban cuando exista un token.",
            how=["Necesitas whatsapp_business_messaging y whatsapp_business_management."]))

    steps.append(_step("subscribed", "App suscrita a la WABA", "unknown", "Se reintenta desde el canal; no bloquea la prueba.",
        where="Tu app → WhatsApp → Configuración de la API → Administrar suscripciones de app",
        how=["Si tu app no aparece suscrita, pulsa «Suscribirse».",
             "Vuelve aquí y pulsa «Comprobar de nuevo»."]))
    steps.append(_step("domain", "Dominio público",
        "done" if public.startswith("https://") else "todo",
        public or "Configura FRONTEND_URL con tu dominio HTTPS.",
        how=["El dominio debe ser HTTPS y público.",
             "Es la misma URL que recibe los webhooks."]))
    steps.append(_step("business", "Verificación de negocio", "manual",
        "La revisa Meta; no se puede automatizar.",
        "https://business.facebook.com/settings",
        where="business.facebook.com → Configuración del negocio → Centro de seguridad",
        how=["Completa los documentos del negocio.",
             "Puede tardar días y no bloquea las pruebas con números de test.",
             "Para conectar la WABA de tus clientes necesitas además ser proveedor de tecnología."]))
    steps.append(_step("test", "Mensaje de prueba",
        "done" if channel and channel.status == "connected" else "todo",
        "Envía un mensaje real al número conectado.",
        where="Con el número de prueba Meta limita a 5 destinatarios verificados",
        how=["Añade tu número en «Para» de la configuración de la API.",
             "Envía el mensaje de prueba desde Meta y confirma que llega.",
             "Después pruébalo desde el Playground con este canal."]))

    scope_by_step = {
        "app": "agency",
        "credentials": "agency",
        "waba": "client",
        "token": "client",
        "webhook": "client",
        "scopes": "client",
        "subscribed": "client",
        "domain": "agency",
        "business": "agency",
        "test": "client",
    }
    for step in steps:
        step["scope"] = scope_by_step.get(step["id"], "client")

    counts = {"green": 0, "amber": 0, "red": 0}
    for step in steps:
        if step["status"] == "done":
            counts["green"] += 1
        elif step["status"] in ("manual", "unknown"):
            counts["amber"] += 1
        else:
            counts["red"] += 1

    return {
        "client_id": client.id,
        "steps": steps,
        "values": {"callback_url": callback, "verify_token": verify, "webhook_fields": "messages"},
        "summary": counts,
        "can_close": counts["red"] == 0,
    }
