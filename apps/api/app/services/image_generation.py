"""Carousel slide image backends: OpenAI, Hugging Face FLUX, local Flux, Ollama, placeholder.

Ollama chat/vision models (llava, qwen2.5, llama, …) cannot generate Flux-quality
ads. Newer Ollama builds expose experimental image models (`x/flux2-klein`,
`x/z-image-turbo`) on macOS; this module calls those if they are installed.

Hugging Face uses Inference Providers (nscale, fal-ai, …). The retired
`hf-inference` router path is skipped (HTTP 410). Non-OpenAI providers never
fall back to OpenAI.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import struct
import zlib
from dataclasses import dataclass

import httpx

from ..config import get_settings


logger = logging.getLogger(__name__)

OPENAI_IMAGE_MODEL = "gpt-image-1-mini"
OPENAI_IMAGE_MODEL_FALLBACK = "gpt-image-1"
DEFAULT_IMAGE_SIZE = "1024x1536"
DEFAULT_HF_IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"
HF_ROUTER = "https://router.huggingface.co"
HF_HUB_MODEL_URL = "https://huggingface.co/api/models/{model}"
# huggingface is remote but billed on HF credits, not OpenAI — never fall back.
LOCAL_IMAGE_PROVIDERS = frozenset({"huggingface", "flux", "ollama", "placeholder"})
IMAGE_PROVIDERS = frozenset({"openai", *LOCAL_IMAGE_PROVIDERS})
IMAGE_PROVIDER_ALIASES = {
    "hf": "huggingface",
    "huggingface-flux": "huggingface",
    "hf-flux": "huggingface",
}
HF_OPENAI_COMPAT_PROVIDERS = frozenset({"nscale", "together", "replicate", "nebius"})
HF_SKIP_PROVIDERS = frozenset({"hf-inference"})
# Names that generate pixels. Vision/chat models must never be used as generators.
OLLAMA_IMAGE_MODEL_PREFIXES = (
    "x/flux",
    "x/z-image",
    "flux",
    "sdxl",
    "stable-diffusion",
    "z-image",
)
OLLAMA_VISION_BLOCKLIST = (
    "llava",
    "bakllava",
    "moondream",
    "minicpm-v",
    "qwen2-vl",
    "qwen2.5-vl",
    "llama3.2-vision",
    "gemma3",
)


@dataclass(frozen=True)
class ImageBackend:
    provider: str
    model: str
    fallback_model: str
    base_url: str
    api_key: str
    size: str
    timeout_seconds: float
    max_workers: int


def normalize_image_provider(raw: str | None) -> str:
    value = (raw or "openai").strip().lower()
    return IMAGE_PROVIDER_ALIASES.get(value, value)


def parse_size(size: str) -> tuple[int, int]:
    raw = (size or DEFAULT_IMAGE_SIZE).lower().replace(" ", "")
    try:
        width_s, height_s = raw.split("x", 1)
        width, height = int(width_s), int(height_s)
    except (TypeError, ValueError):
        return 1024, 1536
    if width < 64 or height < 64:
        return 1024, 1536
    return width, height


def resolve_image_backend(db, agency_id) -> ImageBackend | None:
    """Return the configured slide-image backend, or None if OpenAI is required and missing."""
    settings = get_settings()
    provider = normalize_image_provider(settings.image_provider)
    if provider not in IMAGE_PROVIDERS:
        logger.warning("Unknown IMAGE_PROVIDER=%s", provider)
        return None
    size = (settings.image_size or DEFAULT_IMAGE_SIZE).strip() or DEFAULT_IMAGE_SIZE
    if provider == "placeholder":
        return ImageBackend(
            provider="placeholder",
            model="placeholder",
            fallback_model="",
            base_url="",
            api_key="",
            size=size,
            timeout_seconds=5.0,
            max_workers=1,
        )
    if provider == "huggingface":
        timeout = float(settings.image_local_timeout_seconds or 240.0)
        model = (settings.hf_image_model or DEFAULT_HF_IMAGE_MODEL).strip() or DEFAULT_HF_IMAGE_MODEL
        return ImageBackend(
            provider="huggingface",
            model=model,
            fallback_model=(settings.hf_image_provider or "").strip(),
            base_url=HF_ROUTER,
            api_key=(settings.hf_token or "").strip(),
            size=size,
            timeout_seconds=timeout,
            max_workers=max(1, int(settings.image_local_workers or 1)),
        )
    if provider == "flux":
        timeout = float(settings.image_local_timeout_seconds or 240.0)
        return ImageBackend(
            provider="flux",
            model=(settings.flux_model or "flux-schnell").strip() or "flux-schnell",
            fallback_model="",
            base_url=(settings.flux_base_url or "http://127.0.0.1:7868").rstrip("/"),
            api_key=(settings.flux_api_key or "").strip(),
            size=size,
            timeout_seconds=timeout,
            max_workers=max(1, int(settings.image_local_workers or 1)),
        )
    if provider == "ollama":
        timeout = float(settings.image_local_timeout_seconds or 240.0)
        return ImageBackend(
            provider="ollama",
            model=(settings.ollama_image_model or "x/flux2-klein:4b").strip(),
            fallback_model="",
            base_url=(settings.ollama_base_url or "http://127.0.0.1:11434").rstrip("/"),
            api_key="",
            size=size,
            timeout_seconds=timeout,
            max_workers=max(1, int(settings.image_local_workers or 1)),
        )

    from .providers import resolve_provider_credentials

    try:
        creds = resolve_provider_credentials(db, agency_id, "openai")
    except Exception:  # noqa: BLE001
        creds = None
    if not creds:
        return None
    return ImageBackend(
        provider="openai",
        model=(settings.openai_image_model or OPENAI_IMAGE_MODEL).strip() or OPENAI_IMAGE_MODEL,
        fallback_model=(settings.openai_image_model_fallback or OPENAI_IMAGE_MODEL_FALLBACK).strip()
        or OPENAI_IMAGE_MODEL_FALLBACK,
        base_url=creds[0],
        api_key=creds[1],
        size=size,
        timeout_seconds=float(settings.image_timeout_seconds or 45.0),
        max_workers=max(1, int(settings.image_max_workers or 3)),
    )


def backend_label(backend: ImageBackend) -> str:
    if backend.provider == "openai":
        extra = f" → {backend.fallback_model}" if backend.fallback_model else ""
        return f"OpenAI ({backend.model}{extra})"
    if backend.provider == "huggingface":
        forced = f" via {backend.fallback_model}" if backend.fallback_model else ""
        return f"Hugging Face ({backend.model}{forced})"
    if backend.provider == "flux":
        return f"Flux Schnell ({backend.model} @ {backend.base_url})"
    if backend.provider == "ollama":
        return f"Ollama ({backend.model} @ {backend.base_url})"
    return "local placeholder (not a real ad model)"


# OpenAI published USD per image at quality=high (API default when `quality` is omitted).
# Source: OpenAI model cards / pricing, 1024×1536 portrait used by carousels.
OPENAI_IMAGE_USD_HIGH: dict[str, dict[str, float]] = {
    "gpt-image-1-mini": {"1024x1024": 0.036, "1024x1536": 0.052, "1536x1024": 0.052},
    "gpt-image-1": {"1024x1024": 0.167, "1024x1536": 0.250, "1536x1024": 0.248},
    "gpt-image-1.5": {"1024x1024": 0.133, "1024x1536": 0.200, "1536x1024": 0.200},
}


def openai_image_list_usd(model: str, size: str) -> float | None:
    key = (model or "").strip().split("/")[-1]
    sizes = OPENAI_IMAGE_USD_HIGH.get(key)
    if not sizes:
        return None
    normalized = (size or DEFAULT_IMAGE_SIZE).replace(" ", "").lower()
    if normalized in sizes:
        return sizes[normalized]
    return sizes.get(DEFAULT_IMAGE_SIZE) or next(iter(sizes.values()))


def quote_image_generation(db, agency_id, *, image_count: int) -> dict:
    """Pre-generation cost quote. List prices, not the invoice."""
    count = max(1, min(int(image_count or 1), 12))
    backend = resolve_image_backend(db, agency_id)
    if backend is None:
        per = openai_image_list_usd(OPENAI_IMAGE_MODEL, DEFAULT_IMAGE_SIZE) or 0.052
        fb = openai_image_list_usd(OPENAI_IMAGE_MODEL_FALLBACK, DEFAULT_IMAGE_SIZE) or 0.25
        return {
            "available": False,
            "billable": True,
            "provider": "openai",
            "model": OPENAI_IMAGE_MODEL,
            "fallback_model": OPENAI_IMAGE_MODEL_FALLBACK,
            "size": DEFAULT_IMAGE_SIZE,
            "quality": "high (API default; quality is not sent)",
            "usd_per_image": per,
            "usd_per_image_fallback": fb,
            "image_count": count,
            "usd_typical": round(per * count, 4),
            "usd_if_fallback": round(fb * count, 4),
            "note": "No image backend is ready (add an OpenAI key, set IMAGE_PROVIDER=huggingface with HF_TOKEN, or IMAGE_PROVIDER=flux). Figures are OpenAI list prices if you generate later.",
        }
    if backend.provider != "openai":
        if backend.provider == "huggingface":
            note = (
                "Hugging Face Inference Providers — $0 OpenAI image invoice. "
                "Hugging Face may still consume Inference credits."
            )
        else:
            note = f"Local {backend.provider} — $0 OpenAI image invoice for this run."
        return {
            "available": True,
            "billable": False,
            "provider": backend.provider,
            "model": backend.model,
            "fallback_model": backend.fallback_model or None,
            "size": backend.size,
            "quality": None,
            "usd_per_image": 0.0,
            "usd_per_image_fallback": None,
            "image_count": count,
            "usd_typical": 0.0,
            "usd_if_fallback": 0.0,
            "note": note,
        }
    per = openai_image_list_usd(backend.model, backend.size)
    fb = openai_image_list_usd(backend.fallback_model, backend.size) if backend.fallback_model else None
    if per is None:
        return {
            "available": True,
            "billable": True,
            "provider": "openai",
            "model": backend.model,
            "fallback_model": backend.fallback_model or None,
            "size": backend.size,
            "quality": "high (API default; quality is not sent)",
            "usd_per_image": None,
            "usd_per_image_fallback": fb,
            "image_count": count,
            "usd_typical": None,
            "usd_if_fallback": round(fb * count, 4) if fb else None,
            "note": "OpenAI bills image tokens. This model/size is not in our published per-image table, so we cannot quote a dollar amount.",
        }
    return {
        "available": True,
        "billable": True,
        "provider": "openai",
        "model": backend.model,
        "fallback_model": backend.fallback_model or None,
        "size": backend.size,
        "quality": "high (API default; quality is not sent)",
        "usd_per_image": per,
        "usd_per_image_fallback": fb,
        "image_count": count,
        "usd_typical": round(per * count, 4),
        "usd_if_fallback": round((fb or per) * count, 4),
        "note": "OpenAI list price, not the invoice. A client timeout can still be billed, then we retry the fallback model.",
    }


def empty_usage(model: str, *, skipped_product_edit: bool = False) -> dict:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "model": model,
        "skipped_product_edit": skipped_product_edit,
    }


def generate_slide_image(
    backend: ImageBackend,
    prompt: str,
    *,
    product_image: bytes | None = None,
    product_mime: str | None = None,
) -> tuple[bytes | None, str | None, str | None, dict]:
    """Return (bytes, mime, error, usage). Local backends skip /images/edits."""
    prompt = (prompt or "")[:3500]
    skipped = bool(product_image) and backend.provider != "openai"
    if backend.provider == "placeholder":
        return _placeholder_png(prompt, backend.size), "image/png", None, empty_usage(
            backend.model, skipped_product_edit=skipped
        )
    if backend.provider == "huggingface":
        data, mime, err, usage = _huggingface_image(backend, prompt)
        usage["skipped_product_edit"] = skipped
        return data, mime, err, usage
    if backend.provider == "flux":
        data, mime, err, usage = _flux_image(backend, prompt)
        usage["skipped_product_edit"] = skipped
        return data, mime, err, usage
    if backend.provider == "ollama":
        data, mime, err, usage = _ollama_image(backend, prompt)
        usage["skipped_product_edit"] = skipped
        return data, mime, err, usage
    return _openai_slide_image(
        backend, prompt, product_image=product_image, product_mime=product_mime
    )


def probe_image_backend(db, agency_id) -> dict:
    """Status payload for Settings: current provider, reachability, install hints."""
    settings = get_settings()
    requested = normalize_image_provider(settings.image_provider)
    backend = resolve_image_backend(db, agency_id)
    out = {
        "provider": requested,
        "resolved_provider": backend.provider if backend else None,
        "model": backend.model if backend else None,
        "base_url": backend.base_url if backend else None,
        "size": backend.size if backend else (settings.image_size or DEFAULT_IMAGE_SIZE),
        "ready": False,
        "reachable": False,
        "supports_product_edit": requested == "openai",
        "message": "",
        "install_hint": "",
        "ollama_can_generate_ads": False,
    }
    if requested not in IMAGE_PROVIDERS:
        out["message"] = (
            f"Unknown IMAGE_PROVIDER={requested!r}. Use openai, huggingface, flux, ollama, or placeholder."
        )
        return out
    if backend is None:
        out["message"] = (
            "OpenAI is selected for carousel images, but no OpenAI API key is stored. "
            "Add one in Settings → Providers, or set IMAGE_PROVIDER=huggingface (HF_TOKEN) "
            "or IMAGE_PROVIDER=flux for local tests."
        )
        out["install_hint"] = _flux_install_hint()
        return out
    if backend.provider == "placeholder":
        out["ready"] = True
        out["reachable"] = True
        out["message"] = (
            "Placeholder mode draws solid 4:5 test PNGs. It does not call OpenAI or Flux. "
            "Switch IMAGE_PROVIDER=flux once the sidecar is running."
        )
        out["install_hint"] = _flux_install_hint()
        return out
    if backend.provider == "openai":
        out["ready"] = True
        out["reachable"] = True
        out["message"] = f"Carousel images use OpenAI {backend.model} (fallback {backend.fallback_model})."
        return out
    if backend.provider == "huggingface":
        if not backend.api_key:
            out["message"] = (
                "IMAGE_PROVIDER=huggingface but HF_TOKEN is empty. "
                "Create a token with Inference Providers and set HF_TOKEN in .env.docker."
            )
            out["install_hint"] = _huggingface_install_hint()
            return out
        ok, detail = _probe_huggingface(backend)
        out["reachable"] = ok
        out["ready"] = True
        out["message"] = (
            f"Hugging Face token is set. Model {backend.model}. {detail}"
            if ok
            else (
                f"Hugging Face token is set, but the Hub mapping check failed: {detail}. "
                "Generation may still work via router.huggingface.co."
            )
        )
        out["install_hint"] = _huggingface_install_hint()
        return out
    if backend.provider == "flux":
        ok, detail = _probe_http(backend.base_url, timeout=3.0)
        out["reachable"] = ok
        out["ready"] = ok
        out["message"] = (
            f"Flux endpoint reachable at {backend.base_url}."
            if ok
            else f"Flux sidecar is not reachable at {backend.base_url}: {detail}"
        )
        out["install_hint"] = _flux_install_hint()
        return out
    # ollama
    ok, detail, models = _probe_ollama(backend.base_url, timeout=3.0)
    image_models = [name for name in models if _is_ollama_image_model(name)]
    out["reachable"] = ok
    out["ollama_can_generate_ads"] = bool(image_models)
    out["ready"] = bool(ok and (backend.model in models or image_models))
    if not ok:
        out["message"] = f"Ollama is not reachable at {backend.base_url}: {detail}"
        out["install_hint"] = _ollama_install_hint()
        return out
    if not image_models:
        out["message"] = (
            "Ollama is running, but it has no image-generation model. "
            "Installed models are chat/vision only (they understand photos; they do not paint ads). "
            "Use Flux Schnell (IMAGE_PROVIDER=flux) on this Intel Mac, or pull x/flux2-klein "
            "on Apple Silicon with a 2026+ Ollama."
        )
        out["install_hint"] = _ollama_install_hint() + "\n" + _flux_install_hint()
        return out
    if backend.model not in models:
        out["message"] = (
            f"Ollama has image model(s) {image_models}, but OLLAMA_IMAGE_MODEL={backend.model!r} "
            "is not installed. Pull it or point OLLAMA_IMAGE_MODEL at one of the installed tags."
        )
        out["install_hint"] = _ollama_install_hint()
        return out
    out["message"] = f"Ollama image model {backend.model} is installed."
    out["install_hint"] = (
        "Image generation in Ollama is experimental and primarily Apple Silicon. "
        "If generation fails, use IMAGE_PROVIDER=flux."
    )
    return out


def _huggingface_install_hint() -> str:
    return (
        "Hugging Face FLUX (carousel images without OpenAI):\n"
        "  1. Create a token with Inference Providers at https://huggingface.co/settings/tokens\n"
        "  2. In .env.docker set IMAGE_PROVIDER=huggingface and HF_TOKEN=hf_...\n"
        "  3. Optional: HF_IMAGE_MODEL=black-forest-labs/FLUX.1-schnell (default; FLUX.1-dev is gated)\n"
        "  4. Optional: HF_IMAGE_PROVIDER=nscale to pin a live Hub provider\n"
        "  5. Rebuild/restart the API. This never falls back to OpenAI.\n"
        "The retired hf-inference router path (HTTP 410) is not used."
    )


def _flux_install_hint() -> str:
    return (
        "Local Flux Schnell: from the repo root run\n"
        "  python3 -m venv .venv-flux && source .venv-flux/bin/activate\n"
        "  pip install -r scripts/requirements-flux.txt\n"
        "  python scripts/flux_schnell_server.py\n"
        "Weights are ~12 GB — the server will not download them unless FLUX_ALLOW_DOWNLOAD=1. "
        "Then set IMAGE_PROVIDER=flux and FLUX_BASE_URL=http://host.docker.internal:7868 "
        "in .env.docker and restart the API. This Intel Mac has a 4 GB AMD GPU; Flux will "
        "run on CPU and take several minutes per slide."
    )


def _ollama_install_hint() -> str:
    return (
        "Ollama 0.6.x cannot generate images. Image models (x/flux2-klein, x/z-image-turbo) "
        "need a 2026+ Ollama on macOS, typically Apple Silicon. Do not pull llava for this: "
        "it captions images, it does not create 4:5 ads. Prefer Flux Schnell on this machine."
    )


def _probe_http(base_url: str, *, timeout: float) -> tuple[bool, str]:
    url = base_url.rstrip("/")
    try:
        with httpx.Client(timeout=timeout) as client:
            for path in ("/health", "/v1/models", "/"):
                try:
                    resp = client.get(f"{url}{path}")
                except httpx.HTTPError:
                    continue
                if resp.status_code < 500:
                    return True, f"HTTP {resp.status_code} {path}"
        return False, "no HTTP response from /health, /v1/models, or /"
    except httpx.HTTPError as exc:
        return False, str(exc)[:180]


def _probe_ollama(base_url: str, *, timeout: float) -> tuple[bool, str, list[str]]:
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(f"{base_url.rstrip('/')}/api/tags")
        if resp.status_code >= 400:
            return False, f"HTTP {resp.status_code}", []
        names = [str(item.get("name") or "") for item in (resp.json().get("models") or [])]
        return True, "ok", [name for name in names if name]
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:180], []


def _is_ollama_image_model(name: str) -> bool:
    lowered = (name or "").lower()
    if any(token in lowered for token in OLLAMA_VISION_BLOCKLIST):
        return False
    return any(lowered.startswith(prefix) or f":{prefix}" in lowered for prefix in OLLAMA_IMAGE_MODEL_PREFIXES)


def _parse_token_usage(data: dict) -> dict:
    usage = data.get("usage") or {}
    return {
        "input_tokens": int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or usage.get("completion_tokens") or 0),
    }


def _auth_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _decode_openai_image_payload(data: dict, model: str) -> tuple[bytes | None, str | None, str | None, dict]:
    usage = {**_parse_token_usage(data), "model": model, "skipped_product_edit": False}
    item = (data.get("data") or [{}])[0]
    b64 = item.get("b64_json")
    if not b64 and item.get("url"):
        try:
            with httpx.Client(timeout=45.0) as client:
                img = client.get(item["url"])
        except httpx.HTTPError as exc:
            return None, None, f"image url fetch: {exc!s}"[:180], usage
        if img.status_code >= 400:
            return None, None, f"image url fetch HTTP {img.status_code}", usage
        return img.content, img.headers.get("content-type") or "image/png", None, usage
    if not b64:
        return None, None, f"{model} response missing b64_json", usage
    return base64.b64decode(b64), "image/png", None, usage


def _b64_to_png(raw: str, model: str) -> tuple[bytes | None, str | None, str | None, dict]:
    usage = empty_usage(model)
    token = (raw or "").strip()
    if token.startswith("data:image"):
        token = token.split(",", 1)[-1]
    if not token:
        return None, None, f"{model} empty image payload", usage
    try:
        return base64.b64decode(token), "image/png", None, usage
    except Exception as exc:  # noqa: BLE001
        return None, None, f"{model} b64 decode: {exc!s}"[:160], usage


def _openai_image(backend: ImageBackend, prompt: str, model: str) -> tuple[bytes | None, str | None, str | None, dict]:
    usage = empty_usage(model)
    try:
        with httpx.Client(timeout=backend.timeout_seconds) as client:
            resp = client.post(
                f"{backend.base_url.rstrip('/')}/images/generations",
                headers=_auth_headers(backend.api_key),
                json={"model": model, "prompt": prompt[:3500], "size": backend.size, "n": 1},
            )
        if resp.status_code >= 400:
            detail = resp.text[:180].replace("\n", " ")
            return None, None, f"{model} HTTP {resp.status_code}: {detail}", usage
        return _decode_openai_image_payload(resp.json(), model)
    except httpx.TimeoutException:
        return None, None, f"{model} timeout after {backend.timeout_seconds:.0f}s", usage
    except Exception as exc:  # noqa: BLE001
        return None, None, f"{model} error: {exc!s}"[:180], usage


def _openai_image_edit(
    backend: ImageBackend,
    prompt: str,
    image: bytes,
    mime: str,
    model: str,
) -> tuple[bytes | None, str | None, str | None, dict]:
    ext = "png" if "png" in (mime or "") else "webp" if "webp" in (mime or "") else "jpg"
    usage = empty_usage(model)
    try:
        with httpx.Client(timeout=backend.timeout_seconds) as client:
            resp = client.post(
                f"{backend.base_url.rstrip('/')}/images/edits",
                headers={"Authorization": f"Bearer {backend.api_key}"},
                data={"model": model, "prompt": prompt[:3500], "size": backend.size, "n": "1"},
                files={"image": (f"product.{ext}", image, mime or "image/png")},
            )
        if resp.status_code >= 400:
            detail = resp.text[:180].replace("\n", " ")
            return None, None, f"{model} edit HTTP {resp.status_code}: {detail}", usage
        return _decode_openai_image_payload(resp.json(), model)
    except httpx.TimeoutException:
        return None, None, f"{model} edit timeout after {backend.timeout_seconds:.0f}s", usage
    except Exception as exc:  # noqa: BLE001
        return None, None, f"{model} edit error: {exc!s}"[:180], usage


def _openai_slide_image(
    backend: ImageBackend,
    prompt: str,
    *,
    product_image: bytes | None,
    product_mime: str | None,
) -> tuple[bytes | None, str | None, str | None, dict]:
    if product_image:
        data, mime, err, usage = _openai_image_edit(
            backend, prompt, product_image, product_mime or "image/png", backend.fallback_model
        )
        if data:
            return data, mime or "image/png", None, usage
        data2, mime2, err2, usage2 = _openai_image_edit(
            backend, prompt, product_image, product_mime or "image/png", backend.model
        )
        if data2:
            return data2, mime2 or "image/png", None, usage2
        gen, gmime, gerr, gusage = _openai_image(backend, prompt, backend.model)
        if gen:
            return gen, gmime or "image/png", None, gusage
        return None, None, err or err2 or gerr or "product edit failed", usage or usage2 or gusage
    data, mime, err, usage = _openai_image(backend, prompt, backend.model)
    if data:
        return data, mime or "image/png", None, usage
    data2, mime2, err2, usage2 = _openai_image(backend, prompt, backend.fallback_model)
    if data2:
        return data2, mime2 or "image/png", None, usage2
    return None, None, err or err2 or "unknown image failure", usage2 or usage


def _huggingface_image(backend: ImageBackend, prompt: str) -> tuple[bytes | None, str | None, str | None, dict]:
    usage = empty_usage(backend.model)
    token = (backend.api_key or "").strip()
    if not token:
        return None, None, "HF_TOKEN is empty. Set it in .env.docker for IMAGE_PROVIDER=huggingface.", usage
    last_err = "Hugging Face returned no image"
    try:
        with httpx.Client(timeout=backend.timeout_seconds, follow_redirects=True) as client:
            attempts = _huggingface_attempts(client, backend, prompt[:3500])
            for name, url, payload in attempts:
                try:
                    resp = client.post(
                        url,
                        headers=_huggingface_headers(token, json_accept=True),
                        json=payload,
                    )
                except httpx.TimeoutException:
                    last_err = f"{name} timeout after {backend.timeout_seconds:.0f}s"
                    continue
                except httpx.HTTPError as exc:
                    last_err = f"{name} network error: {exc!s}"[:180]
                    continue
                if resp.status_code in {401, 403}:
                    return None, None, (
                        f"Hugging Face token rejected (HTTP {resp.status_code}). "
                        f"{_huggingface_http_detail(resp)}"
                    )[:280], usage
                if resp.status_code == 402:
                    return None, None, (
                        "Hugging Face Inference credits are exhausted (HTTP 402). "
                        f"{_huggingface_http_detail(resp)}"
                    )[:280], usage
                if resp.status_code in {400, 404, 410, 422, 429, 503}:
                    last_err = f"{name} HTTP {resp.status_code}: {_huggingface_http_detail(resp)}"
                    continue
                if resp.status_code >= 400:
                    last_err = f"{name} HTTP {resp.status_code}: {_huggingface_http_detail(resp)}"
                    continue
                data, mime, err = _huggingface_bytes_from_response(client, resp, token)
                if data:
                    return data, mime or "image/png", None, usage
                last_err = err or f"{name} did not return image bytes"
    except httpx.TimeoutException:
        return None, None, f"huggingface timeout after {backend.timeout_seconds:.0f}s", usage
    except Exception as exc:  # noqa: BLE001
        return None, None, f"huggingface error: {exc!s}"[:180], usage
    return None, None, last_err[:280], usage


def _huggingface_headers(token: str, *, json_accept: bool) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if json_accept:
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
    return headers


def _huggingface_http_detail(resp: httpx.Response) -> str:
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        return (resp.text or "").replace("\n", " ")[:180]
    if isinstance(body, dict):
        err = body.get("error") or body.get("message") or body
        return str(err).replace("\n", " ")[:180]
    return str(body)[:180]


def _looks_like_image(content: bytes, content_type: str = "") -> bool:
    ctype = (content_type or "").lower()
    if ctype.startswith("image/"):
        return True
    return content.startswith(b"\x89PNG") or content.startswith(b"\xff\xd8") or content.startswith(b"RIFF")


def _huggingface_live_providers(client: httpx.Client, model: str) -> list[tuple[str, str]]:
    url = HF_HUB_MODEL_URL.format(model=model) + "?expand[]=inferenceProviderMapping"
    try:
        resp = client.get(url, timeout=12.0)
    except httpx.HTTPError:
        return []
    if resp.status_code >= 400:
        return []
    try:
        mapping = (resp.json() or {}).get("inferenceProviderMapping") or {}
    except Exception:  # noqa: BLE001
        return []
    live: list[tuple[str, str]] = []
    for provider, info in mapping.items():
        if not isinstance(info, dict):
            continue
        if info.get("status") != "live":
            continue
        if info.get("task") not in (None, "text-to-image"):
            continue
        name = str(provider)
        if name in HF_SKIP_PROVIDERS:
            continue
        live.append((name, str(info.get("providerId") or model)))
    return live


def _probe_huggingface(backend: ImageBackend) -> tuple[bool, str]:
    try:
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            live = _huggingface_live_providers(client, backend.model)
    except httpx.HTTPError as exc:
        return False, str(exc)[:180]
    if not live:
        return False, "no live text-to-image providers on the Hub mapping (router may still work)"
    names = ", ".join(name for name, _pid in live[:6])
    return True, f"Live Hub providers: {names}."


def _huggingface_attempts(
    client: httpx.Client, backend: ImageBackend, prompt: str
) -> list[tuple[str, str, dict]]:
    width, height = parse_size(backend.size)
    preferred = (backend.fallback_model or "").strip().lower()
    live = _huggingface_live_providers(client, backend.model)
    if preferred:
        live = [item for item in live if item[0] == preferred] or [(preferred, backend.model)]
    attempts: list[tuple[str, str, dict]] = []
    seen: set[str] = set()

    def add(name: str, url: str, payload: dict) -> None:
        if name in seen:
            return
        seen.add(name)
        attempts.append((name, url, payload))

    for provider, provider_id in live:
        if provider in HF_OPENAI_COMPAT_PROVIDERS:
            add(
                provider,
                f"{HF_ROUTER}/{provider}/v1/images/generations",
                {
                    "model": provider_id,
                    "prompt": prompt,
                    "n": 1,
                    "size": backend.size,
                    "response_format": "b64_json",
                    "width": width,
                    "height": height,
                },
            )
        elif provider == "fal-ai":
            add(
                "fal-ai",
                f"{HF_ROUTER}/fal-ai/{provider_id}",
                {
                    "prompt": prompt,
                    "sync_mode": True,
                    "image_size": {"width": width, "height": height},
                },
            )
        elif provider == "wavespeed":
            add(
                "wavespeed",
                f"{HF_ROUTER}/wavespeed/{provider_id}",
                {"prompt": prompt},
            )
        else:
            add(
                provider,
                f"{HF_ROUTER}/{provider}/{provider_id}",
                {"prompt": prompt, "inputs": prompt},
            )
    if not preferred:
        add(
            "router-openai",
            f"{HF_ROUTER}/v1/images/generations",
            {
                "model": backend.model,
                "prompt": prompt,
                "n": 1,
                "size": backend.size,
                "response_format": "b64_json",
            },
        )
    if not attempts:
        add(
            "nscale",
            f"{HF_ROUTER}/nscale/v1/images/generations",
            {
                "model": backend.model,
                "prompt": prompt,
                "n": 1,
                "size": backend.size,
                "response_format": "b64_json",
            },
        )
    return attempts


def _huggingface_bytes_from_response(
    client: httpx.Client, resp: httpx.Response, token: str
) -> tuple[bytes | None, str | None, str | None]:
    content = resp.content or b""
    ctype = resp.headers.get("content-type") or ""
    if _looks_like_image(content, ctype):
        mime = ctype.split(";")[0] if ctype.startswith("image/") else "image/png"
        return content, mime, None
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        return None, None, "Hugging Face response was not JSON or image bytes"
    if not isinstance(body, dict):
        return None, None, "Hugging Face JSON was not an object"

    data = body.get("data")
    if isinstance(data, list) and data:
        item = data[0] if isinstance(data[0], dict) else {}
        decoded = _huggingface_image_from_item(client, item, token)
        if decoded[0] or decoded[2]:
            return decoded

    images = body.get("images")
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, str):
            return _huggingface_resolve_image_ref(client, first, token)
        if isinstance(first, dict):
            decoded = _huggingface_image_from_item(client, first, token)
            if decoded[0] or decoded[2]:
                return decoded

    # fal-ai / some providers put a lone image field on the root object
    for key in ("image", "b64_json", "url"):
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            return _huggingface_resolve_image_ref(client, value, token)
    return None, None, "Hugging Face JSON missing image / b64_json"


def _huggingface_image_from_item(
    client: httpx.Client, item: dict, token: str
) -> tuple[bytes | None, str | None, str | None]:
    for key in ("b64_json", "image", "url"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            decoded, mime, err = _huggingface_resolve_image_ref(client, value, token)
            if decoded:
                return decoded, mime, None
            if err and key != "url":
                return None, None, err
    return None, None, "item had no decodable image field"


def _huggingface_resolve_image_ref(
    client: httpx.Client, ref: str, token: str
) -> tuple[bytes | None, str | None, str | None]:
    """Decode data: URLs / raw b64 in-process; only HTTP(S) URLs are fetched."""
    text = (ref or "").strip()
    if not text:
        return None, None, "empty image reference"
    if text.startswith(("http://", "https://")):
        return _huggingface_fetch_url(client, text, token)
    # fal-ai sync_mode uses data:image/...;base64,... — never HTTP GET that.
    # OpenAI-compat providers return raw b64_json without a data: prefix.
    decoded, mime, err, _usage = _b64_to_png(text, "huggingface")
    return decoded, mime, err


def _huggingface_fetch_url(
    client: httpx.Client, url: str, token: str
) -> tuple[bytes | None, str | None, str | None]:
    # fal-ai sync_mode often returns data:image/...;base64,... in the "url" field.
    # GETting that raises httpx "URL too long" — decode locally instead.
    if url.startswith("data:image"):
        decoded, mime, err, _usage = _b64_to_png(url, "huggingface")
        return decoded, mime, err
    if len(url) > 8000:
        return None, None, "image url too long (expected http(s) or data:image)"
    try:
        img = client.get(url, headers=_huggingface_headers(token, json_accept=False))
    except httpx.HTTPError as exc:
        return None, None, f"image url fetch: {exc!s}"[:180]
    except Exception as exc:  # noqa: BLE001 — InvalidURL etc.
        return None, None, f"image url fetch: {exc!s}"[:180]
    if img.status_code >= 400:
        return None, None, f"image url fetch HTTP {img.status_code}"
    content = img.content or b""
    if not _looks_like_image(content, img.headers.get("content-type") or ""):
        return None, None, "fetched url was not an image"
    ctype = (img.headers.get("content-type") or "image/png").split(";")[0]
    return content, ctype or "image/png", None


def _flux_image(backend: ImageBackend, prompt: str) -> tuple[bytes | None, str | None, str | None, dict]:
    last_err = "flux endpoint returned no image"
    for size in (backend.size, "768x1024", "1024x1024"):
        w, h = parse_size(size)
        data, mime, err, usage = _flux_try(backend, prompt, w, h)
        if data:
            return data, mime, None, usage
        last_err = err or last_err
        if size == backend.size and err and "size" not in (err or "").lower() and "dimension" not in (err or "").lower():
            if "HTTP 4" in err or "HTTP 5" in err or "timeout" in err.lower() or "connect" in err.lower():
                break
    return None, None, last_err, empty_usage(backend.model)


def _flux_try(
    backend: ImageBackend, prompt: str, width: int, height: int
) -> tuple[bytes | None, str | None, str | None, dict]:
    usage = empty_usage(backend.model)
    base = backend.base_url.rstrip("/")
    size = f"{width}x{height}"
    payload_openai = {
        "model": backend.model,
        "prompt": prompt[:3500],
        "size": size,
        "n": 1,
        "response_format": "b64_json",
        "width": width,
        "height": height,
    }
    payload_simple = {"prompt": prompt[:3500], "width": width, "height": height, "model": backend.model}
    payload_a1111 = {
        "prompt": prompt[:3500],
        "width": width,
        "height": height,
        "steps": 4,
        "cfg_scale": 1,
        "sampler_name": "Euler",
    }
    attempts = (
        ("POST", "/v1/images/generations", payload_openai),
        ("POST", "/generate", payload_simple),
        ("POST", "/sdapi/v1/txt2img", payload_a1111),
    )
    last_err = None
    try:
        with httpx.Client(timeout=backend.timeout_seconds) as client:
            for method, path, body in attempts:
                try:
                    resp = client.request(
                        method, f"{base}{path}", headers=_auth_headers(backend.api_key), json=body
                    )
                except httpx.ConnectError as exc:
                    return None, None, (
                        f"flux connect failed at {base}: {exc!s}. "
                        "Start scripts/flux_schnell_server.py or set FLUX_BASE_URL."
                    )[:240], usage
                if resp.status_code == 404:
                    last_err = f"{path} HTTP 404"
                    continue
                if resp.status_code >= 400:
                    last_err = f"{path} HTTP {resp.status_code}: {resp.text[:140].replace(chr(10), ' ')}"
                    continue
                parsed = _parse_flux_body(resp, backend.model)
                if parsed[0]:
                    return parsed
                last_err = parsed[2]
        return None, None, last_err or "flux: no compatible endpoint (/v1/images/generations, /generate, /sdapi/v1/txt2img)", usage
    except httpx.TimeoutException:
        return None, None, f"flux timeout after {backend.timeout_seconds:.0f}s at {base}", usage
    except Exception as exc:  # noqa: BLE001
        return None, None, f"flux error: {exc!s}"[:180], usage


def _parse_flux_body(resp: httpx.Response, model: str) -> tuple[bytes | None, str | None, str | None, dict]:
    ctype = (resp.headers.get("content-type") or "").lower()
    if "image/" in ctype:
        return resp.content, ctype.split(";")[0] or "image/png", None, empty_usage(model)
    try:
        data = resp.json()
    except Exception:  # noqa: BLE001
        return None, None, "flux response was not JSON or image bytes", empty_usage(model)
    if not isinstance(data, dict):
        return None, None, "flux JSON was not an object", empty_usage(model)
    if data.get("data"):
        return _decode_openai_image_payload(data, model)
    for key in ("b64_json", "image", "images"):
        value = data.get(key)
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, dict):
            value = value.get("b64_json") or value.get("image")
        if isinstance(value, str) and value:
            return _b64_to_png(value, model)
    return None, None, "flux JSON missing image / b64_json", empty_usage(model)


def _ollama_image(backend: ImageBackend, prompt: str) -> tuple[bytes | None, str | None, str | None, dict]:
    if not _is_ollama_image_model(backend.model):
        return None, None, (
            f"{backend.model} is not an image generator. llava/qwen/llama only understand images. "
            "Use IMAGE_PROVIDER=flux or pull x/flux2-klein on a 2026+ Ollama (Apple Silicon)."
        ), empty_usage(backend.model)
    width, height = parse_size(backend.size)
    usage = empty_usage(backend.model)
    base = backend.base_url.rstrip("/")
    openai_payload = {
        "model": backend.model,
        "prompt": prompt[:3500],
        "size": backend.size,
        "n": 1,
        "response_format": "b64_json",
    }
    generate_payload = {
        "model": backend.model,
        "prompt": prompt[:3500],
        "stream": False,
        "options": {"width": width, "height": height},
    }
    try:
        with httpx.Client(timeout=backend.timeout_seconds) as client:
            try:
                resp = client.post(
                    f"{base}/v1/images/generations",
                    headers={"Content-Type": "application/json"},
                    json=openai_payload,
                )
                if resp.status_code < 400:
                    parsed = _decode_openai_image_payload(resp.json(), backend.model)
                    if parsed[0]:
                        return parsed
            except httpx.HTTPError:
                pass
            resp = client.post(
                f"{base}/api/generate",
                headers={"Content-Type": "application/json"},
                json=generate_payload,
            )
        if resp.status_code >= 400:
            detail = resp.text[:180].replace("\n", " ")
            return None, None, f"ollama HTTP {resp.status_code}: {detail}", usage
        data = resp.json()
        token = data.get("image") or ""
        if not token and isinstance(data.get("images"), list) and data["images"]:
            token = data["images"][0]
        if token:
            decoded = _b64_to_png(str(token), backend.model)
            if decoded[0]:
                prompt_tokens = int((data.get("prompt_eval_count") or 0))
                eval_tokens = int((data.get("eval_count") or 0))
                usage = {
                    "input_tokens": prompt_tokens,
                    "output_tokens": eval_tokens,
                    "model": backend.model,
                    "skipped_product_edit": False,
                }
                return decoded[0], decoded[1], None, usage
        return None, None, (
            "Ollama returned no image. This build may be too old (need 2026+ with x/flux2-klein) "
            "or image generation may be Apple Silicon only."
        ), usage
    except httpx.ConnectError as exc:
        return None, None, f"ollama connect failed at {base}: {exc!s}"[:200], usage
    except httpx.TimeoutException:
        return None, None, f"ollama timeout after {backend.timeout_seconds:.0f}s", usage
    except Exception as exc:  # noqa: BLE001
        return None, None, f"ollama error: {exc!s}"[:180], usage


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def _placeholder_png(prompt: str, size: str) -> bytes:
    """Deterministic 4:5 PNG so tests do not call a paid API. Not a real ad."""
    width, height = parse_size(size)
    # Keep Instagram 4:5 but cap pixels so this stays cheap in Python.
    width = min(max(width, 64), 512)
    height = min(max(height, 80), 640)
    digest = hashlib.sha256((prompt or "slide").encode("utf-8")).digest()
    r0, g0, b0 = digest[0], digest[1], digest[2]
    r1, g1, b1 = 255 - digest[3], 255 - digest[4], 255 - digest[5]
    rows = []
    for y in range(height):
        t = y / max(height - 1, 1)
        row = bytearray(1 + width * 3)
        row[0] = 0
        for x in range(width):
            s = x / max(width - 1, 1)
            r = int(r0 * (1 - t) + r1 * t)
            g = int(g0 * (1 - s) + g1 * s)
            b = int(b0 * (1 - t) * (1 - s) + b1 * t * s)
            # Light frame so it is obvious this is a test plate.
            if x < 8 or y < 8 or x >= width - 8 or y >= height - 8:
                r, g, b = 240, 240, 240
            i = 1 + x * 3
            row[i : i + 3] = (r & 255, g & 255, b & 255)
        rows.append(bytes(row))
    raw = b"".join(rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )
