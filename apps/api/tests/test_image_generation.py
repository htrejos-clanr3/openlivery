"""Slide image backends: placeholder, Flux HTTP, Ollama guardrails, usage rows."""

from unittest.mock import MagicMock

import httpx

from app.services.image_generation import (
    IMAGE_PROVIDERS,
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
    assert body["provider"] in IMAGE_PROVIDERS
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


TINY_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII="


def test_huggingface_missing_token_is_not_ready(monkeypatch):
    from app.config import Settings

    monkeypatch.setattr(
        "app.services.image_generation.get_settings",
        lambda: Settings(image_provider="huggingface", hf_token=""),
    )
    backend = resolve_image_backend(MagicMock(), "agency")
    assert backend is not None
    assert backend.provider == "huggingface"
    status = probe_image_backend(MagicMock(), "agency")
    assert status["ready"] is False
    assert "HF_TOKEN" in status["message"]
    data, mime, err, usage = generate_slide_image(backend, "an ad")
    assert data is None
    assert err and "HF_TOKEN" in err
    assert usage["model"] == "black-forest-labs/FLUX.1-schnell"


def test_huggingface_nscale_b64(monkeypatch):
    from app.config import Settings

    monkeypatch.setattr(
        "app.services.image_generation.get_settings",
        lambda: Settings(
            image_provider="hf",
            hf_token="hf_test_token",
            hf_image_model="black-forest-labs/FLUX.1-schnell",
        ),
    )

    class FakeResp:
        def __init__(self, status_code=200, payload=None, headers=None, text=""):
            self.status_code = status_code
            self._payload = payload
            self.headers = headers or {"content-type": "application/json"}
            self.text = text
            self.content = b""

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, headers=None, **kwargs):
            assert "huggingface.co/api/models" in url
            return FakeResp(
                payload={
                    "inferenceProviderMapping": {
                        "hf-inference": {
                            "status": "live",
                            "task": "text-to-image",
                            "providerId": "dead",
                        },
                        "nscale": {
                            "status": "live",
                            "task": "text-to-image",
                            "providerId": "black-forest-labs/FLUX.1-schnell",
                        },
                    }
                }
            )

        def post(self, url, headers=None, json=None):
            assert "/nscale/v1/images/generations" in url
            assert json["prompt"]
            assert json["response_format"] == "b64_json"
            assert headers["Authorization"] == "Bearer hf_test_token"
            return FakeResp(payload={"data": [{"b64_json": TINY_PNG_B64}]})

    monkeypatch.setattr("app.services.image_generation.httpx.Client", FakeClient)
    backend = resolve_image_backend(MagicMock(), "agency")
    assert backend.provider == "huggingface"
    data, mime, err, usage = generate_slide_image(backend, "vertical 4:5 ad")
    assert err is None
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert mime == "image/png"
    assert usage["input_tokens"] == 0
    assert usage["model"] == "black-forest-labs/FLUX.1-schnell"


def test_huggingface_fal_data_url_is_decoded_not_fetched(monkeypatch):
    """fal-ai sync_mode puts a data:image URL in images[].url — must not HTTP GET it."""
    from app.config import Settings

    monkeypatch.setattr(
        "app.services.image_generation.get_settings",
        lambda: Settings(
            image_provider="huggingface",
            hf_token="hf_test_token",
            hf_image_model="black-forest-labs/FLUX.1-schnell",
            hf_image_provider="fal-ai",
        ),
    )
    data_url = "data:image/png;base64," + TINY_PNG_B64

    class FakeResp:
        def __init__(self, status_code=200, payload=None, headers=None, text=""):
            self.status_code = status_code
            self._payload = payload
            self.headers = headers or {"content-type": "application/json"}
            self.text = text
            self.content = b""

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, headers=None, **kwargs):
            if "huggingface.co/api/models" in url:
                return FakeResp(
                    payload={
                        "inferenceProviderMapping": {
                            "fal-ai": {
                                "status": "live",
                                "task": "text-to-image",
                                "providerId": "fal-ai/flux/schnell",
                            },
                        }
                    }
                )
            raise AssertionError(f"must not HTTP GET image refs: {url[:80]}")

        def post(self, url, headers=None, json=None):
            assert "/fal-ai/" in url
            return FakeResp(payload={"images": [{"url": data_url}]})

    monkeypatch.setattr("app.services.image_generation.httpx.Client", FakeClient)
    backend = resolve_image_backend(MagicMock(), "agency")
    data, mime, err, _usage = generate_slide_image(backend, "vertical 4:5 ad")
    assert err is None, err
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert mime == "image/png"


def test_hf_alias_and_quote_are_not_openai(monkeypatch):

    from app.config import Settings
    from app.services.image_generation import quote_image_generation

    monkeypatch.setattr(
        "app.services.image_generation.get_settings",
        lambda: Settings(image_provider="huggingface", hf_token="hf_test_token"),
    )
    quote = quote_image_generation(MagicMock(), "agency", image_count=3)
    assert quote["available"] is True
    assert quote["billable"] is False
    assert quote["provider"] == "huggingface"
    assert quote["usd_typical"] == 0.0
