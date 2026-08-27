"""Resolve next fire time for weekly schedule windows (no exact calendar dates in UI)."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def _parse_hhmm(value: str, *, fallback: time) -> time:
    raw = (value or "").strip()
    try:
        hour, minute = raw.split(":")
        return time(hour=int(hour), minute=int(minute))
    except Exception:  # noqa: BLE001
        return fallback


def next_weekly_window_start(
    *,
    weekdays: list[int],
    window_start: str,
    window_end: str | None = None,
    timezone_name: str = "America/Bogota",
    after: datetime | None = None,
) -> datetime:
    """Next occurrence of a weekday window start, as UTC-aware datetime.

    weekdays: 0=Monday … 6=Sunday (Python weekday()).
    Publishes at window_start (beginning of the slot). window_end is for UX/display.
    """
    days = sorted({int(d) for d in (weekdays or []) if 0 <= int(d) <= 6})
    if not days:
        raise ValueError("Select at least one weekday")
    try:
        tz = ZoneInfo(timezone_name or "America/Bogota")
    except Exception:  # noqa: BLE001
        tz = ZoneInfo("America/Bogota")
    start_t = _parse_hhmm(window_start, fallback=time(8, 0))
    # Validate end >= start when provided (same-day windows only).
    if window_end:
        end_t = _parse_hhmm(window_end, fallback=time(10, 0))
        if end_t <= start_t:
            raise ValueError("Window end must be after start")

    now = after.astimezone(tz) if after else datetime.now(tz)
    for offset in range(0, 15):
        day = (now + timedelta(days=offset)).date()
        if day.weekday() not in days:
            continue
        candidate = datetime(
            day.year, day.month, day.day, start_t.hour, start_t.minute, tzinfo=tz
        )
        if candidate > now:
            return candidate.astimezone(timezone.utc)
    raise ValueError("Could not resolve next schedule window")


def format_weekly_window_label(
    *,
    weekdays: list[int],
    window_start: str,
    window_end: str,
    timezone_name: str,
    language: str = "es",
) -> str:
    es = not (language or "es").startswith("en")
    names_es = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    names_en = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    names = names_es if es else names_en
    days = [names[d] for d in sorted({int(x) for x in (weekdays or []) if 0 <= int(x) <= 6})]
    if not days:
        return ""
    day_part = ", ".join(days)
    tz = (timezone_name or "America/Bogota").split("/")[-1].replace("_", " ")
    return f"{day_part} · {window_start}–{window_end} ({tz})"
