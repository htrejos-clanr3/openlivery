"""Background poller for scheduled Instagram publications."""

from __future__ import annotations

import asyncio
import logging

from ..config import get_settings
from ..database import SessionLocal
from .instagram_publishing import execute_due_publications

logger = logging.getLogger(__name__)
_task: asyncio.Task | None = None
_stop: asyncio.Event | None = None


async def _loop(stop: asyncio.Event) -> None:
    settings = get_settings()
    interval = max(5.0, float(settings.instagram_scheduler_interval_seconds))
    while not stop.is_set():
        try:
            db = SessionLocal()
            try:
                count = await execute_due_publications(db)
                if count:
                    logger.info("instagram_scheduler processed=%s", count)
            finally:
                db.close()
        except Exception:  # noqa: BLE001
            logger.exception("instagram_scheduler_error")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


def start_scheduler() -> None:
    global _task, _stop
    settings = get_settings()
    if not settings.instagram_scheduler_enabled:
        return
    if _task and not _task.done():
        return
    _stop = asyncio.Event()
    _task = asyncio.create_task(_loop(_stop), name="instagram-publication-scheduler")


async def stop_scheduler() -> None:
    global _task, _stop
    if _stop is not None:
        _stop.set()
    if _task:
        try:
            await asyncio.wait_for(asyncio.shield(_task), timeout=2)
        except (asyncio.TimeoutError, asyncio.CancelledError, RuntimeError):
            _task.cancel()
            try:
                await _task
            except (asyncio.CancelledError, RuntimeError):
                pass
        _task = None
    _stop = None
