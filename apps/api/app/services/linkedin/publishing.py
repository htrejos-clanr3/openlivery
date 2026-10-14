"""Official LinkedIn Posts API adapter for personal text and multi-image posts."""

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

    def _headers(self) -> dict[str, str]:
        settings = get_settings()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "LinkedIn-Version": settings.linkedin_api_version,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def _owner_urn(self) -> str:
        return f"urn:li:person:{self.member_id}"

    async def publish_text(self, text: str) -> str:
        if mock_enabled():
            return f"urn:li:share:mock-{secrets.token_hex(8)}"
        payload = {
            "author": self._owner_urn(),
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
        return await self._create_post(payload)

    async def publish_multi_image(
        self,
        text: str,
        images: list[tuple[bytes, str, str]],
    ) -> str:
        """Publish an organic MultiImage post (2–20 images).

        Each image is (bytes, mime_type, alt_text).
        """
        if len(images) < 2 or len(images) > 20:
            raise LinkedInPublishingError("LinkedIn MultiImage requires between 2 and 20 images")
        if mock_enabled():
            return f"urn:li:share:mock-multi-{secrets.token_hex(8)}"

        image_refs: list[dict[str, str]] = []
        for data, mime, alt in images:
            image_urn = await self._upload_image(data, mime_type=mime or "image/jpeg")
            image_refs.append({"id": image_urn, "altText": (alt or "")[:120]})

        payload = {
            "author": self._owner_urn(),
            "commentary": text[:3000],
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {"multiImage": {"images": image_refs}},
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        return await self._create_post(payload)

    async def _upload_image(self, data: bytes, *, mime_type: str) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            init = await client.post(
                "https://api.linkedin.com/rest/images?action=initializeUpload",
                headers=self._headers(),
                json={"initializeUploadRequest": {"owner": self._owner_urn()}},
            )
            if init.status_code >= 400:
                raise self._error_from_response(init, "LinkedIn image initializeUpload failed")
            value = (init.json() or {}).get("value") or {}
            upload_url = value.get("uploadUrl")
            image_urn = value.get("image")
            if not upload_url or not image_urn:
                raise LinkedInPublishingError("LinkedIn did not return an upload URL for the image")

            put = await client.put(
                upload_url,
                content=data,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": mime_type.split(";")[0] or "application/octet-stream",
                },
            )
            if put.status_code >= 400:
                raise LinkedInPublishingError(
                    "LinkedIn image binary upload failed",
                    status_code=put.status_code,
                    raw=put.text[:500],
                )
        return str(image_urn)

    async def _create_post(self, payload: dict) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.linkedin.com/rest/posts",
                headers=self._headers(),
                json=payload,
            )
        if response.status_code >= 400:
            raise self._error_from_response(response, "LinkedIn publish failed")
        post_id = response.headers.get("x-restli-id") or response.headers.get("X-RestLi-Id")
        if post_id:
            return post_id
        try:
            body = response.json()
        except Exception:  # noqa: BLE001
            body = {}
        return str(body.get("id") or body.get("value") or "published")

    @staticmethod
    def _error_from_response(response: httpx.Response, fallback: str) -> LinkedInPublishingError:
        try:
            detail = response.json()
        except Exception:  # noqa: BLE001
            detail = {"message": response.text}
        message = detail.get("message") or detail.get("error_description") or fallback
        return LinkedInPublishingError(message, status_code=response.status_code, raw=detail)
