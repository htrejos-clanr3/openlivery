"""Official LinkedIn Posts API adapter for personal text posts."""

from __future__ import annotations

import secrets
from typing import Any

import httpx

from ...config import get_settings
from .oauth import mock_enabled


class LinkedInPublishingError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, raw: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.raw = raw


class LinkedInPublishingProvider:
    def __init__(self, *, member_id: str, access_token: str):
        self.member_id = member_id
        self.access_token = access_token

    async def publish_text(self, text: str) -> str:
        if mock_enabled():
            return f"urn:li:share:mock-{secrets.token_hex(8)}"
        settings = get_settings()
        payload = {
            "author": f"urn:li:person:{self.member_id}",
            "commentary": text,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.linkedin.com/rest/posts",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                    "LinkedIn-Version": settings.linkedin_api_version,
                    "X-Restli-Protocol-Version": "2.0.0",
                },
                json=payload,
            )
        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:  # noqa: BLE001
                detail = {"message": response.text}
            raise LinkedInPublishingError(
                detail.get("message") or detail.get("error_description") or "LinkedIn publish failed",
                status_code=response.status_code,
                raw=detail,
            )
        post_id = response.headers.get("x-restli-id") or response.headers.get("X-RestLi-Id")
        if post_id:
            return post_id
        try:
            body = response.json()
        except Exception:  # noqa: BLE001
            body = {}
        return str(body.get("id") or body.get("value") or "published")
