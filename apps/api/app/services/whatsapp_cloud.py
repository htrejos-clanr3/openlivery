"""Thin client for the WhatsApp Business Cloud API (Meta Graph API).

Each channel brings its own Meta app credentials; the access token is decrypted
by the caller and never logged. Errors surface as HTTPException with safe
messages (Meta's error detail, never the credentials).
"""

import httpx
from fastapi import HTTPException

from ..config import get_settings

MAX_MEDIA_BYTES = 20 * 1024 * 1024
# Hard limit of the Cloud API for a text message body.
MAX_TEXT_LENGTH = 4096
GRAPH_TIMEOUT = 30


def _graph_url(path: str) -> str:
    return f"{get_settings().meta_graph_base_url.rstrip('/')}/{path.lstrip('/')}"


def _graph_error(response: httpx.Response) -> str:
    try:
        message = response.json().get("error", {}).get("message")
    except ValueError:
        message = None
    return message or f"Meta API returned status {response.status_code}"


async def _graph_request(method: str, url: str, access_token: str, **kwargs) -> httpx.Response:
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        async with httpx.AsyncClient(timeout=GRAPH_TIMEOUT) as client:
            return await client.request(method, url, headers=headers, **kwargs)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not reach the Meta API.") from exc


async def verify_phone_number(access_token: str, phone_number_id: str) -> dict:
    """Validate the credentials and return the number's public profile."""
    settings = get_settings()
    if settings.meta_mock_mode or access_token == "mock-access-token" or phone_number_id.startswith("mock-"):
        return {
            "display_phone_number": "+57 300 000 0000",
            "verified_name": "Mock Business",
            "id": phone_number_id,
        }
    response = await _graph_request(
        "GET",
        _graph_url(f"{phone_number_id}?fields=display_phone_number,verified_name"),
        access_token,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Credential check failed: {_graph_error(response)}")
    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Invalid response from the Meta API.") from exc


async def send_text(access_token: str, phone_number_id: str, to: str, body: str) -> str | None:
    """Send a text message; returns the outbound message id (wamid)."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body[:MAX_TEXT_LENGTH]},
    }
    response = await _graph_request("POST", _graph_url(f"{phone_number_id}/messages"), access_token, json=payload)
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"WhatsApp could not send the message: {_graph_error(response)}")
    try:
        messages = response.json().get("messages") or []
        return messages[0].get("id") if messages else None
    except ValueError:
        return None


async def fetch_media(access_token: str, media_id: str) -> tuple[bytes, str]:
    """Download an inbound media file: resolve the short-lived URL, then fetch
    it with the same token. Returns (data, mime_type)."""
    lookup = await _graph_request("GET", _graph_url(media_id), access_token)
    if lookup.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Could not resolve the media file: {_graph_error(lookup)}")
    try:
        info = lookup.json()
        url, mime = info["url"], info.get("mime_type") or "application/octet-stream"
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=502, detail="Invalid media response from the Meta API.") from exc
    download = await _graph_request("GET", url, access_token)
    if download.status_code >= 400 or len(download.content) > MAX_MEDIA_BYTES:
        raise HTTPException(status_code=502, detail="Could not download the media file.")
    return download.content, mime


async def list_message_templates(access_token: str, waba_id: str) -> list[dict]:
    """Fetch message templates for a WABA (live from Graph; no local cache)."""
    settings = get_settings()
    if settings.meta_mock_mode or access_token == "mock-access-token" or waba_id.startswith("mock-"):
        return [
            {
                "id": "mock-tpl-1",
                "name": "hello_world",
                "language": "en_US",
                "status": "APPROVED",
                "category": "UTILITY",
                "components": [{"type": "BODY", "text": "Hello {{1}}"}],
            }
        ]
    if not waba_id.strip():
        raise HTTPException(status_code=400, detail="WABA ID is required to list templates")
    response = await _graph_request(
        "GET",
        _graph_url(f"{waba_id}?fields=message_templates{{name,status,language,category,id,components}}"),
        access_token,
    )
    if response.status_code >= 400:
        # Fallback shape used by older Graph versions.
        response = await _graph_request(
            "GET",
            _graph_url(f"{waba_id}/message_templates"),
            access_token,
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Could not list templates: {_graph_error(response)}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Invalid template response from Meta.") from exc
    if isinstance(payload.get("message_templates"), dict):
        data = payload["message_templates"].get("data") or []
    else:
        data = payload.get("data") or []
    return [item for item in data if isinstance(item, dict)]


async def send_template(
    access_token: str,
    phone_number_id: str,
    to: str,
    *,
    name: str,
    language: str,
    body_parameters: list[str] | None = None,
) -> str | None:
    """Send an approved WhatsApp template message; returns wamid when present."""
    settings = get_settings()
    if settings.meta_mock_mode or access_token == "mock-access-token" or phone_number_id.startswith("mock-"):
        return "wamid.mock-template"
    components: list[dict] = []
    if body_parameters:
        components.append(
            {
                "type": "body",
                "parameters": [{"type": "text", "text": value} for value in body_parameters],
            }
        )
    payload: dict = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": name,
            "language": {"code": language},
        },
    }
    if components:
        payload["template"]["components"] = components
    response = await _graph_request("POST", _graph_url(f"{phone_number_id}/messages"), access_token, json=payload)
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"WhatsApp could not send the template: {_graph_error(response)}")
    try:
        messages = response.json().get("messages") or []
        return messages[0].get("id") if messages else None
    except ValueError:
        return None
