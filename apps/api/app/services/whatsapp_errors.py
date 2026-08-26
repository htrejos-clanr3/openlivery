"""Translate Meta / WhatsApp Cloud errors into operator-friendly messages."""

from __future__ import annotations

import re


def humanize_whatsapp_error(detail: str | None) -> dict:
    """Return {message, code, technical} without leaking tokens."""
    technical = (detail or "Unknown error").strip()[:500]
    lowered = technical.lower()

    rules: list[tuple[tuple[str, ...], str, str]] = [
        (("oauthexception", "session has expired", "error validating access token", "token has expired"), "TOKEN_EXPIRED", "No fue posible validar el acceso a WhatsApp. El permiso puede haber vencido o sido revocado."),
        (("permission", "(#200)", "insufficient", "not authorized"), "PERMISSION_ERROR", "Permisos insuficientes en Meta para operar este número de WhatsApp."),
        (("phone number", "does not exist", "unsupported get request"), "PHONE_NOT_FOUND", "Número no disponible o Phone Number ID incorrecto."),
        (("waba", "whatsapp business account"), "WABA_NOT_FOUND", "Cuenta de WhatsApp Business no encontrada."),
        (("webhook",), "WEBHOOK_ERROR", "Webhook no configurado o no responde correctamente."),
        (("restricted", "disabled", "account is locked"), "ACCOUNT_RESTRICTED", "La cuenta de WhatsApp está restringida por Meta."),
        (("could not reach", "timed out", "connection"), "NETWORK_ERROR", "No se pudo contactar con la API de Meta. Inténtalo de nuevo."),
    ]
    for needles, code, message in rules:
        if any(n in lowered for n in needles):
            return {"message": message, "code": code, "technical": technical}

    # Strip EAAG… token-looking fragments from any residual message.
    scrubbed = re.sub(r"EAA[A-Za-z0-9]+", "[redacted]", technical)
    return {
        "message": "No fue posible validar el acceso a WhatsApp. Revisa la conexión o vuelve a autorizar con Meta.",
        "code": "UNKNOWN",
        "technical": scrubbed,
    }
