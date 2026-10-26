"""Guided Meta setup status for one client.

The wizard shows ten steps. Everything that can be derived from stored state is
computed here; the two Graph probes are best-effort and degrade to "unknown"
instead of failing the page.
"""

from __future__ import annotations

import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..security import decrypt_secret, encrypt_secret
from ..models import Agency, Client, User, WhatsAppCloudChannel, now_utc

router = APIRouter(prefix="/clients/{client_id}/meta-setup", tags=["Meta setup"])


class ChannelIn(BaseModel):
    phone_number_id: str | None = None
    waba_id: str | None = None
    access_token: str | None = None
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

    agency_row = db.get(Agency, user.agency_id)
    app_registered = bool(agency_row and agency_row.meta_app_id)
    has_app = bool(agency_row and agency_row.meta_app_id and agency_row.encrypted_meta_app_secret)
    steps: list[dict] = []
    def _mockish(value: str | None) -> bool:
        return not value or value.startswith("mock")

    has_credentials = bool(
        channel and not _mockish(channel.phone_number_id) and not _mockish(channel.waba_id)
    )
    has_token = bool(channel and channel.encrypted_access_token)
    steps.append(_step("app", "App de Meta", "done" if app_registered else "todo",
        "Crea la app una vez por agencia y registra su App ID en el paso 2.",
        "https://developers.facebook.com/apps",
        where="developers.facebook.com/apps → Crear app → Nombre y correo → Siguiente → Casos de uso",
        how=["Elige el caso de uso «Conéctate con los clientes a través de WhatsApp».",
             "Si ya la creaste, ábrela en «Mis apps».",
             "Registra su App ID y su secret en el paso 2: hasta entonces este paso no puede ponerse verde."]))
    steps.append(_step("credentials", "App ID y secret",
        "done" if has_app else "todo",
        "Sin estos dos datos no se puede validar nada.",
        where="Tu app → Configuración de la app → Básica",
        how=["Copia «Identificador de la app».",
             "Pulsa «Mostrar» en «Clave secreta» y cópiala.",
             "Pega ambos en Configuración → Meta: se guardan una vez para toda la agencia."]))
    steps.append(_step("waba", "WABA y número", "done" if has_credentials else "todo",
        f"Phone number ID {channel.phone_number_id}" if has_credentials else "Los dos identificadores del número y de la cuenta.",
        where="Caso de uso de WhatsApp → Configuración básica → Paso 2: Configuración de producción → Registra tu número de teléfono",
        how=["En «Registra tu número de teléfono de WhatsApp» pulsa Agregar (o el lápiz).",
             "En el modal elige «Agregar un número nuevo» → Continuar; si ya tienes uno, «Usar solo un nombre visible».",
             "Verifica el número con el código que te envíen.",
             "Copia el Phone number ID y el Messaging Account ID (antes WABA ID) y pégalos en el paso 3.",
             "Si Meta responde «already in use by another WhatsApp account», el número ya está en otra cuenta: elimínala desde el teléfono (Ajustes → Cuenta → Eliminar cuenta) o usa otro número. Meta no migra números entre cuentas."]))
    steps.append(_step("token", "Token del system user", "done" if has_token else "todo",
        "El token temporal caduca; el permanente es el que deja el canal estable.",
        where="Misma página → sección «Enviar mensaje» → Paso 1: Genera un token",
        how=["Pulsa «Generar token»: Meta emite uno permanente para la cuenta.",
             "Cópialo y pégalo en Configuración avanzada del canal.",
             "Alternativa con control total: business.facebook.com → Usuarios del sistema."]))

    if channel and has_token:
        from .. import security as security_module
        decrypt = (getattr(security_module, "decrypt_secret", None)
                   or getattr(security_module, "decrypt_text", None)
                   or getattr(security_module, "decrypt", None))
        token = decrypt(channel.encrypted_access_token) if decrypt and channel.encrypted_access_token else None
        webhook_status, webhook_detail = "unknown", "No se pudo comprobar contra Meta."
        scopes_status, scopes_detail = "unknown", "No se pudieron leer los permisos concedidos."
        if token:
            if token.startswith("mock"):
                for entry in steps:
                    if entry["id"] == "token":
                        entry["status"] = "todo"
                        entry["detail"] = (
                            "El token guardado es de prueba (mock). Genera el token permanente en Meta y pégalo aquí."
                        )
                token = None
            info = _graph(f"{channel.phone_number_id}", token, params={"fields": "webhook_configuration"})
            if isinstance(info, dict):
                config = info.get("webhook_configuration") or {}
                actual = config.get("phone_number") if isinstance(config, dict) else None
                webhook_status = "done" if actual and actual.rstrip("/") == callback.rstrip("/") else "todo"
                webhook_detail = "Meta confirma la URL en el número." if webhook_status == "done" else "Meta no tiene registrada esta URL en el número."
            if webhook_status != "done" and channel.waba_id:
                apps = _graph(f"{channel.waba_id}/subscribed_apps", token)
                for app in (apps or {}).get("data") or []:
                    uri = (app or {}).get("override_callback_uri")
                    if isinstance(uri, str) and uri.rstrip("/") == callback.rstrip("/"):
                        webhook_status, webhook_detail = "done", "Meta confirma la URL a nivel de la cuenta (WABA)."
                        break
            if (webhook_status != "done" and agency_row and agency_row.meta_app_id
                    and agency_row.encrypted_meta_app_secret and decrypt):
                app_token = f"{agency_row.meta_app_id}|{decrypt(agency_row.encrypted_meta_app_secret)}"
                subs = _graph(f"{agency_row.meta_app_id}/subscriptions", app_token)
                for item in (subs or {}).get("data") or []:
                    url = (item or {}).get("callback_url")
                    fields = (item or {}).get("fields") or []
                    if isinstance(url, str) and url.rstrip("/") == callback.rstrip("/"):
                        webhook_status = "done"
                        webhook_detail = "Meta confirma la URL a nivel de app." + (
                            "" if "messages" in fields else " Falta suscribir el campo messages."
                        )
                        break
            debug = _graph("debug_token", token, params={"input_token": token})
            data = (debug or {}).get("data") or {}
            granted = set(data.get("scopes") or [])
            if granted:
                missing = sorted(REQUIRED_SCOPES - granted)
                scopes_status = "todo" if missing else "done"
                scopes_detail = f"Falta {', '.join(missing)}" if missing else "Permisos completos."
        for entry in steps:
            if entry["id"] == "token":
                entry["detail"] = f"{entry['detail']} Permisos del token: {scopes_detail}"
                if scopes_status == "done":
                    entry["status"] = "done"
        steps.append(_step("webhook", "Webhook registrado", webhook_status, webhook_detail, value=callback,
            where="Misma página → «Configurar webhooks» (arriba del todo)",
            how=["Pega la URL de callback y el token de verificación de abajo.",
                 "Pulsa «Verificar y guardar».",
                 "Suscribe el campo messages."]))
    else:
        steps.append(_step("webhook", "Webhook registrado", "todo", "Se registra cuando exista un token.", value=callback,
            where="Misma página → «Configurar webhooks» (arriba del todo)",
            how=["Primero completa los pasos 2 a 4.",
                 "Después pega la URL de callback y el token de verificación."]))

    steps.append(_step("subscribed", "App suscrita a la WABA", "unknown", "Se reintenta desde el canal; no bloquea la prueba.",
        where="Misma página → configuración del número",
        how=["Comprueba que la app aparezca suscrita a la cuenta de WhatsApp Business.",
             "Vuelve aquí y pulsa «Comprobar de nuevo»."]))
    steps.append(_step("business", "Verificación de negocio", "manual",
        "La revisa Meta; no se puede automatizar.",
        "https://business.facebook.com/settings",
        where="Caso de uso → Paso 3: Verificación del negocio (en tu panel ya aparece en verde)",
        how=["Los documentos se suben en business.facebook.com → Centro de seguridad.",
             "Añade método de pago: hace falta para mensajes iniciados por la empresa; las respuestas de servicio tienen 1.000 gratis al mes por número.",
             "Para conectar la WABA de tus clientes necesitas además «Conviértete en proveedor de tecnología»."]))
    steps.append(_step("test", "Mensaje de prueba",
        "done" if channel and channel.status == "connected" else "todo",
        "Envía un mensaje real al número conectado.",
        where="Misma página → «Enviar mensaje» → Paso 2: envía un mensaje desde tu número registrado",
        how=["Añade tu número como destinatario verificado.",
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
        "channel": {
            "phone_number_id": channel.phone_number_id if channel else "",
            "waba_id": (channel.waba_id or "") if channel else "",
            "has_token": bool(channel and channel.encrypted_access_token),
        },
    }


@router.put("/channel")
def save_channel(
    client_id: uuid.UUID,
    payload: ChannelIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client, channel = _channel(db, user, client_id)
    if channel is None:
        raise HTTPException(
            status_code=400,
            detail="Create the channel on its page first; this form updates an existing one.",
        )
    if payload.phone_number_id is not None:
        channel.phone_number_id = payload.phone_number_id.strip()[:80]
    if payload.waba_id is not None:
        channel.waba_id = payload.waba_id.strip()[:80] or None
    if payload.access_token:
        channel.encrypted_access_token = encrypt_secret(payload.access_token.strip())
    channel.updated_at = now_utc()
    db.commit()
    return {"ok": True}


def _number(phone: dict, waba_id: str, waba_name: str) -> dict:
    return {
        "phone_number_id": phone.get("id", ""),
        "display_phone_number": phone.get("display_phone_number", ""),
        "verified_name": phone.get("verified_name", ""),
        "waba_id": waba_id,
        "waba_name": waba_name,
    }


@router.get("/discover")
def discover_numbers(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client, channel = _channel(db, user, client_id)
    if channel is None or not channel.encrypted_access_token:
        raise HTTPException(
            status_code=400,
            detail="Guarda primero el token del canal: sin token Meta no devuelve nada.",
        )
    token = decrypt_secret(channel.encrypted_access_token)
    numbers: list[dict] = []
    seen: set[str] = set()

    def add(phone: dict, waba_id: str, waba_name: str) -> None:
        item = _number(phone, waba_id, waba_name)
        if item["phone_number_id"] and item["phone_number_id"] not in seen:
            seen.add(item["phone_number_id"])
            numbers.append(item)

    businesses = _graph("me/businesses", token, params={"fields": "id,name", "limit": "25"}) or {}
    for business in businesses.get("data") or []:
        business_id = (business or {}).get("id")
        if not business_id:
            continue
        wabas = _graph(f"{business_id}/owned_whatsapp_business_accounts", token,
                       params={"fields": "id,name"}) or {}
        for waba in wabas.get("data") or []:
            waba_id = (waba or {}).get("id")
            if not waba_id:
                continue
            phones = _graph(f"{waba_id}/phone_numbers", token,
                            params={"fields": "id,display_phone_number,verified_name"}) or {}
            for phone in phones.get("data") or []:
                add(phone or {}, waba_id, (waba or {}).get("name", ""))

    if not numbers and channel.waba_id and not channel.waba_id.startswith("mock"):
        phones = _graph(f"{channel.waba_id}/phone_numbers", token,
                        params={"fields": "id,display_phone_number,verified_name"}) or {}
        for phone in phones.get("data") or []:
            add(phone or {}, channel.waba_id, "")

    return {"numbers": numbers, "waba_id": channel.waba_id or ""}
