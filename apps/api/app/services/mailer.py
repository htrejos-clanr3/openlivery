"""Outbound email over SMTP.

Password reset is the only mail this product sends. Sending is disabled when
SMTP_HOST is empty, so local and test environments keep working without a mail
server: callers get a boolean and never an exception.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from ..config import get_settings

logger = logging.getLogger("openlivery.mailer")


def is_configured() -> bool:
    return bool(get_settings().smtp_host)


def password_reset_link(token: str, purpose: str) -> str:
    base = get_settings().frontend_url.rstrip("/")
    return f"{base}/login?token={token}&purpose={purpose}"


def send_email(*, to: str, subject: str, text: str) -> bool:
    settings = get_settings()
    if not settings.smtp_host:
        logger.warning("smtp is not configured; skipping mail to %s", to)
        return False

    message = EmailMessage()
    message["From"] = settings.smtp_from or settings.smtp_user or "no-reply@localhost"
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)

    try:
        if settings.smtp_use_ssl:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
        with server:
            if settings.smtp_starttls and not settings.smtp_use_ssl:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
    except Exception:  # noqa: BLE001 — a mail failure must not break the request
        logger.exception("failed to send mail to %s", to)
        return False
    return True
