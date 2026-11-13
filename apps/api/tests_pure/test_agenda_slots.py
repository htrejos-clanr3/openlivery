"""Pure slot arithmetic: no database, no model calls."""

from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.services.agenda import _free, _slots_in_window, _windows_for_day

BOGOTA = ZoneInfo("America/Bogota")


def rule(weekday: int, start=time(9), end=time(12), slot=60, buffer=0, active=True):
    return SimpleNamespace(
        weekday=weekday,
        start_time=start,
        end_time=end,
        slot_minutes=slot,
        buffer_minutes=buffer,
        is_active=active,
    )


def exception(day: date, closed=True, start=None, end=None):
    return SimpleNamespace(exception_date=day, is_closed=closed, start_time=start, end_time=end)


def test_slots_without_buffer():
    slots = _slots_in_window(date(2026, 11, 9), time(9), time(12), 60, 0, BOGOTA)
    assert [s[0].strftime("%H:%M") for s in slots] == ["09:00", "10:00", "11:00"]


def test_slots_with_buffer_breaks_last_slot():
    slots = _slots_in_window(date(2026, 11, 9), time(9), time(12), 60, 30, BOGOTA)
    assert [s[0].strftime("%H:%M") for s in slots] == ["09:00", "10:30"]


def test_day_without_rule_has_no_windows():
    assert _windows_for_day(date(2026, 11, 9), [rule(weekday=1)], []) == []


def test_closed_exception_removes_the_day():
    day = date(2026, 11, 9)
    assert _windows_for_day(day, [rule(weekday=day.weekday())], [exception(day)]) == []


def test_open_exception_overrides_hours():
    day = date(2026, 11, 9)
    windows = _windows_for_day(
        day, [rule(weekday=day.weekday())], [exception(day, closed=False, start=time(15), end=time(17))]
    )
    assert windows == [(time(15), time(17), 60, 0)]


def test_overlap_is_never_free():
    slot = (datetime(2026, 11, 9, 9, tzinfo=BOGOTA), datetime(2026, 11, 9, 10, tzinfo=BOGOTA))
    busy = [(datetime(2026, 11, 9, 9, 30, tzinfo=BOGOTA), datetime(2026, 11, 9, 10, 30, tzinfo=BOGOTA))]
    assert _free(slot, busy) is False


def test_adjacent_booking_is_free():
    slot = (datetime(2026, 11, 9, 10, tzinfo=BOGOTA), datetime(2026, 11, 9, 11, tzinfo=BOGOTA))
    busy = [(datetime(2026, 11, 9, 9, tzinfo=BOGOTA), datetime(2026, 11, 9, 10, tzinfo=BOGOTA))]
    assert _free(slot, busy) is True


def test_daylight_saving_shift_keeps_wall_clock_hours():
    """A zone with DST must still produce the same local start times."""
    madrid = ZoneInfo("Europe/Madrid")
    before = _slots_in_window(date(2026, 10, 24), time(9), time(11), 60, 0, madrid)
    after = _slots_in_window(date(2026, 10, 26), time(9), time(11), 60, 0, madrid)
    assert [s[0].strftime("%H:%M") for s in before] == ["09:00", "10:00"]
    assert [s[0].strftime("%H:%M") for s in after] == ["09:00", "10:00"]
    assert before[0][0].utcoffset() != after[0][0].utcoffset()
