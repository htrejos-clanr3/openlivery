"""Slide image backends: placeholder, Flux HTTP, Ollama guardrails, usage rows."""

from unittest.mock import MagicMock

import httpx

from app.services.image_generation import (
    ImageBackend,
    generate_slide_image,
    parse_size,
    probe_image_backend,
    resolve_image_backend,
)
from app.services.usage import summarize_usage, usage_entry


def _backend(**kwargs) -> ImageBackend:
    defaults = dict(
        provider="flux",
        model="flux-schnell",
        fallback_model="",
        base_url="http://127.0.0.1:7868",
        api_key="",
        size="1024x1536",
        timeout_seconds=5.0,
        max_workers=1,
    )
    defaults.update(kwargs)
    return ImageBackend(**defaults)


def test_parse_size_defaults():
    assert parse_size("1024x1536") == (1024, 1536)
    assert parse_size("nope") == (1024, 1536)


def test_placeholder_png_is_png(monkeypatch):
    from app.config import Settings, get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.image_generation.get_settings",
        lambda: Settings(image_provider="placeholder"),
    )
    backend = resolve_image_backend(MagicMock(), "agency")
    assert backend is not None
    assert backend.provider == "placeholder"
    data, mime, err, usage = generate_slide_image(backend, "headline about coffee")
    assert err is None
    assert mime == "image/png"
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert usage["model"] == "placeholder"
    assert usage["input_tokens"] == 0


def test_flux_openai_compatible_payload(monkeypatch):
    payload = {"data": [{"b64_json": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII="}]}

    class FakeResp:
        status_code = 200
        headers = {"content-type": "application/json"}
        text = ""

        def json(self):
            return payload

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, method, url, headers=None, json=None):
            assert "/v1/images/generations" in url
            assert json["prompt"]
            assert json["size"] == "1024x1536"
            return FakeResp()

    monkeypatch.setattr("app.services.image_generation.httpx.Client", FakeClient)
    data, mime, err, usage = generate_slide_image(_backend(), "vertical 4:5 ad")
    assert err is None
    assert data
    assert mime == "image/png"
    assert usage["model"] == "flux-schnell"


def test_ollama_rejects_llava():
    backend = _backend(provider="ollama", model="llava:latest", base_url="http://127.0.0.1:11434")
    data, mime, err, usage = generate_slide_image(backend, "an ad")
    assert data is None
    assert err and "not an image generator" in err
    assert usage["input_tokens"] == 0


def test_summarize_usage_keeps_zero_token_images():
    rows = [
        usage_entry(kind="copy", provider="deepseek", model="deepseek-chat", input_tokens=0, output_tokens=0),
        usage_entry(kind="image", provider="flux", model="flux-schnell", input_tokens=0, output_tokens=0, label="slide 1"),
    ]
    summary = summarize_usage(rows)
    assert len(summary["items"]) == 1
    assert summary["items"][0]["provider"] == "flux"
    assert summary["estimated_usd"] == 0


def test_image_generation_status_endpoint(authenticated_client):
    listed = authenticated_client.get("/api/providers/image-generation")
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["provider"] in {"openai", "flux", "ollama", "placeholder"}
    assert "message" in body
    assert "install_hint" in body


def test_probe_unknown_provider(monkeypatch):
    from app.config import Settings

    monkeypatch.setattr(
        "app.services.image_generation.get_settings",
        lambda: Settings(image_provider="nope"),
    )
    status = probe_image_backend(MagicMock(), "agency")
    assert status["ready"] is False
    assert "Unknown" in status["message"]


def test_flux_connect_error_is_actionable(monkeypatch):
    class BoomClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, *args, **kwargs):
            req = httpx.Request("POST", "http://127.0.0.1:7868/v1/images/generations")
            raise httpx.ConnectError("connection refused", request=req)

    monkeypatch.setattr("app.services.image_generation.httpx.Client", BoomClient)
    data, mime, err, usage = generate_slide_image(_backend(), "prompt")
    assert data is None
    assert err and "flux_schnell_server" in err
    assert usage["input_tokens"] == 0
