"""Instagram Graph Content Publishing provider (real + mock).

Official flow (Meta Content Publishing):
  POST /{ig-user-id}/media → container
  GET  /{container-id}?fields=status_code → FINISHED
  POST /{ig-user-id}/media_publish?creation_id=…
"""

from __future__ import annotations

import asyncio
import secrets
import time
from typing import Any

import httpx

from ..config import get_settings


class InstagramGraphError(Exception):
    def __init__(self, message: str, *, code: str | None = None, raw: Any = None):
        super().__init__(message)
        self.code = code
        self.raw = raw


def mock_enabled() -> bool:
    return bool(get_settings().instagram_publishing_mock_mode)


def _graph_base() -> str:
    return get_settings().meta_graph_base_url.rstrip("/")


async def _graph_request(
    method: str,
    path: str,
    *,
    access_token: str,
    params: dict | None = None,
    data: dict | None = None,
) -> dict:
    if mock_enabled():
        raise InstagramGraphError("Mock mode: unexpected real Graph call", code="MOCK")
    url = f"{_graph_base()}/{path.lstrip('/')}"
    query = dict(params or {})
    query["access_token"] = access_token
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.request(method, url, params=query, data=data)
    try:
        payload = response.json()
    except Exception as exc:  # noqa: BLE001
        raise InstagramGraphError(f"Invalid Graph response ({response.status_code})", code=str(response.status_code)) from exc
    if response.status_code >= 400 or payload.get("error"):
        err = payload.get("error") or {}
        raise InstagramGraphError(
            err.get("message") or response.text or "Graph API error",
            code=str(err.get("code") or response.status_code),
            raw=payload,
        )
    return payload if isinstance(payload, dict) else {"data": payload}


class InstagramPublishingProvider:
    """Adapter around IG User media / media_publish endpoints."""

    def __init__(self, *, ig_user_id: str, access_token: str):
        self.ig_user_id = ig_user_id
        self.access_token = access_token
        self._mock_store: dict[str, dict] = {}

    async def create_image_container(
        self, *, image_url: str, caption: str | None = None, is_carousel_item: bool = False
    ) -> str:
        if mock_enabled():
            cid = f"mock_img_{secrets.token_hex(6)}"
            self._mock_store[cid] = {"status_code": "FINISHED", "type": "IMAGE"}
            return cid
        data: dict[str, Any] = {"image_url": image_url}
        if caption and not is_carousel_item:
            data["caption"] = caption
        if is_carousel_item:
            data["is_carousel_item"] = "true"
        result = await _graph_request("POST", f"{self.ig_user_id}/media", access_token=self.access_token, data=data)
        return str(result["id"])

    async def create_video_container(
        self,
        *,
        video_url: str,
        media_type: str = "REELS",
        caption: str | None = None,
        cover_url: str | None = None,
        is_carousel_item: bool = False,
    ) -> str:
        if mock_enabled():
            cid = f"mock_vid_{secrets.token_hex(6)}"
            self._mock_store[cid] = {"status_code": "IN_PROGRESS", "type": media_type, "ready_at": time.time() + 0.5}
            return cid
        data: dict[str, Any] = {"video_url": video_url, "media_type": media_type}
        if caption and not is_carousel_item:
            data["caption"] = caption
        if cover_url:
            data["cover_url"] = cover_url
        if is_carousel_item:
            data["is_carousel_item"] = "true"
            data["media_type"] = "VIDEO"
        result = await _graph_request("POST", f"{self.ig_user_id}/media", access_token=self.access_token, data=data)
        return str(result["id"])

    async def create_carousel_container(self, *, children: list[str], caption: str | None = None) -> str:
        if mock_enabled():
            cid = f"mock_car_{secrets.token_hex(6)}"
            self._mock_store[cid] = {"status_code": "FINISHED", "type": "CAROUSEL", "children": children}
            return cid
        data: dict[str, Any] = {
            "media_type": "CAROUSEL",
            "children": ",".join(children),
        }
        if caption:
            data["caption"] = caption
        result = await _graph_request("POST", f"{self.ig_user_id}/media", access_token=self.access_token, data=data)
        return str(result["id"])

    async def get_container_status(self, container_id: str) -> str:
        if mock_enabled():
            entry = self._mock_store.get(container_id) or {"status_code": "FINISHED"}
            if entry.get("status_code") == "IN_PROGRESS" and time.time() >= float(entry.get("ready_at") or 0):
                entry["status_code"] = "FINISHED"
            return str(entry.get("status_code") or "FINISHED")
        result = await _graph_request(
            "GET",
            container_id,
            access_token=self.access_token,
            params={"fields": "status_code"},
        )
        return str(result.get("status_code") or "IN_PROGRESS")

    async def wait_until_finished(self, container_id: str) -> str:
        settings = get_settings()
        max_attempts = max(1, settings.instagram_container_poll_max_attempts)
        delay = max(0.2, settings.instagram_container_poll_delay_seconds)
        last = "IN_PROGRESS"
        for _ in range(max_attempts):
            last = await self.get_container_status(container_id)
            if last in {"FINISHED", "PUBLISHED"}:
                return last
            if last in {"ERROR", "EXPIRED"}:
                raise InstagramGraphError(f"Container status {last}", code=last)
            await asyncio.sleep(delay)
        raise InstagramGraphError(f"Container polling timeout (last={last})", code="TIMEOUT")

    async def publish_container(self, container_id: str) -> str:
        if mock_enabled():
            return f"mock_pub_{secrets.token_hex(6)}"
        result = await _graph_request(
            "POST",
            f"{self.ig_user_id}/media_publish",
            access_token=self.access_token,
            data={"creation_id": container_id},
        )
        return str(result["id"])

    async def get_media_permalink(self, media_id: str) -> str | None:
        if mock_enabled():
            return f"https://www.instagram.com/p/{media_id}/"
        try:
            result = await _graph_request(
                "GET",
                media_id,
                access_token=self.access_token,
                params={"fields": "permalink"},
            )
            return result.get("permalink")
        except InstagramGraphError:
            return None

    async def content_publishing_limit(self) -> dict:
        if mock_enabled():
            return {"quota_usage": 0, "config": {"quota_total": 50, "quota_duration": 86400}}
        result = await _graph_request(
            "GET",
            f"{self.ig_user_id}/content_publishing_limit",
            access_token=self.access_token,
            params={"fields": "quota_usage,config"},
        )
        data = result.get("data") or []
        return data[0] if data else {"quota_usage": 0, "config": {}}

    async def debug_token_or_me(self) -> dict:
        if mock_enabled():
            return {"id": self.ig_user_id, "username": "mock_user"}
        return await _graph_request(
            "GET",
            self.ig_user_id,
            access_token=self.access_token,
            params={"fields": "id,username,name"},
        )
