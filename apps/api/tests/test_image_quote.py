"""Pre-generation image cost quotes (OpenAI list prices)."""

from app.services.image_generation import IMAGE_PROVIDERS, openai_image_list_usd, quote_image_generation


def test_openai_image_list_usd_known_sizes():
    assert openai_image_list_usd("gpt-image-1-mini", "1024x1536") == 0.052
    assert openai_image_list_usd("gpt-image-1", "1024x1536") == 0.25
    assert openai_image_list_usd("unknown-model", "1024x1536") is None


def test_image_quote_endpoint(authenticated_client):
    res = authenticated_client.get("/api/carousels/image-quote?count=8")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["image_count"] == 8
    assert body["provider"] in IMAGE_PROVIDERS
    assert "usd_typical" in body
    if body["billable"] and body["usd_per_image"] is not None:
        assert body["usd_typical"] == round(body["usd_per_image"] * 8, 4)


def test_quote_helper_without_backend(monkeypatch):
    monkeypatch.setattr("app.services.image_generation.resolve_image_backend", lambda db, agency_id: None)
    quote = quote_image_generation(None, None, image_count=8)
    assert quote["available"] is False
    assert quote["billable"] is True
    assert quote["usd_typical"] == round(0.052 * 8, 4)
    assert quote["usd_if_fallback"] == round(0.25 * 8, 4)
