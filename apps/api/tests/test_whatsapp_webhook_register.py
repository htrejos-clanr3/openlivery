"""Unit tests for Meta webhook override registration (no live Graph calls)."""

import asyncio
from unittest.mock import AsyncMock, patch

from app.services.whatsapp_cloud_webhook_register import register_webhook_for_number


def test_register_webhook_mock_token():
    result = asyncio.run(
        register_webhook_for_number(
            waba_id="waba",
            phone_number_id="mock-phone",
            access_token="mock-access-token",
            webhook_url="https://app.example/api/public/whatsapp-cloud/channels/x/webhook",
            verify_token="verify",
        )
    )
    assert result.ok is True
    assert result.code == "mock"


def test_register_skips_foreign_waba_override():
    async def fake_graph(method, path, token, *, json_body=None):
        if method == "GET" and path.endswith("/subscribed_apps"):
            return 200, {"data": [{"override_callback_uri": "https://foreign.example/hook/secret"}]}, None
        if method == "GET" and "webhook_configuration" in path:
            return 200, {"webhook_configuration": {"phone_number": None}}, None
        if method == "POST" and json_body and json_body.get("webhook_configuration", {}).get("override_callback_uri") == "":
            return 200, {"success": True}, None
        raise AssertionError(f"unexpected graph call {method} {path} {json_body}")

    with patch(
        "app.services.whatsapp_cloud_webhook_register._graph_json",
        new=AsyncMock(side_effect=fake_graph),
    ):
        result = asyncio.run(
            register_webhook_for_number(
                waba_id="waba-1",
                phone_number_id="phone-1",
                access_token="real-token",
                webhook_url="https://app.example/api/public/whatsapp-cloud/channels/x/webhook",
                verify_token="verify",
            )
        )
    assert result.ok is True
    assert result.code == "skipped_waba_override"
    assert result.host == "foreign.example"


def test_register_phone_override_success():
    webhook = "https://app.example/api/public/whatsapp-cloud/channels/x/webhook"

    async def fake_graph(method, path, token, *, json_body=None):
        if method == "GET" and path.endswith("/subscribed_apps"):
            return 200, {"data": []}, None
        if method == "POST" and path.endswith("/subscribed_apps"):
            return 200, {"success": True}, None
        if method == "POST" and path == "phone-1":
            assert json_body["webhook_configuration"]["override_callback_uri"] == webhook
            return 200, {"success": True}, None
        if method == "GET" and "webhook_configuration" in path:
            return 200, {"webhook_configuration": {"phone_number": webhook, "application": "https://app.meta"}}, None
        raise AssertionError(f"unexpected graph call {method} {path}")

    with patch(
        "app.services.whatsapp_cloud_webhook_register._graph_json",
        new=AsyncMock(side_effect=fake_graph),
    ):
        result = asyncio.run(
            register_webhook_for_number(
                waba_id="waba-1",
                phone_number_id="phone-1",
                access_token="real-token",
                webhook_url=webhook,
                verify_token="verify",
            )
        )
    assert result.ok is True
    assert result.code == "registered"
    assert result.app_without_webhook is False
