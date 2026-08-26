"""Humanize Instagram / Graph API publishing errors for operators."""

from __future__ import annotations


def classify_instagram_error(code: str | None, message: str) -> str:
    text = f"{code or ''} {message}".lower()
    if any(x in text for x in ("oauth", "access token", "session has expired", "(#190)", "permission")):
        return "AUTH"
    if any(x in text for x in ("rate limit", "(#4)", "(#17)", "(#32)", "throttle", "publishing limit", "quota")):
        return "RATE_LIMIT"
    if any(x in text for x in ("invalid", "format", "aspect", "duration", "too large", "(#100)", "media")):
        return "VALIDATION"
    if any(x in text for x in ("timeout", "temporarily", "try again", "5xx", "connection", "network")):
        return "TRANSIENT"
    return "PERMANENT"


def humanize_instagram_error(*, code: str | None = None, message: str = "", technical: str | None = None) -> dict:
    error_class = classify_instagram_error(code, message)
    friendly = {
        "AUTH": "Instagram connection needs attention. Reconnect the account and try again.",
        "RATE_LIMIT": "Instagram publishing limit reached. Wait before publishing more content.",
        "VALIDATION": "Instagram rejected this media. Check format, size, aspect ratio, or carousel rules.",
        "TRANSIENT": "Temporary Instagram/API issue. You can retry shortly.",
        "PERMANENT": "Instagram rejected this publication.",
    }.get(error_class, "Instagram rejected this publication.")
    return {
        "message": friendly,
        "error_class": error_class,
        "code": code,
        "technical": technical or message or None,
    }
