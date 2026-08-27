"""Local Flux Schnell HTTP sidecar for OpenLivery carousel tests.

Does not download the ~12 GB weights unless FLUX_ALLOW_DOWNLOAD=1.
Does not import torch until a generate request (or --preload).

Usage:
  python3 -m venv .venv-flux && source .venv-flux/bin/activate
  pip install -r scripts/requirements-flux.txt
  python scripts/flux_schnell_server.py
  FLUX_ALLOW_DOWNLOAD=1 python scripts/flux_schnell_server.py   # explicit opt-in
  FLUX_MODEL_PATH=/path/to/FLUX.1-schnell python scripts/flux_schnell_server.py

Env:
  FLUX_HOST          default 127.0.0.1
  FLUX_PORT          default 7868
  FLUX_MODEL         default black-forest-labs/FLUX.1-schnell
  FLUX_MODEL_PATH    local snapshot directory (skips Hub id)
  FLUX_ALLOW_DOWNLOAD  set to 1 to pull weights from Hugging Face
  FLUX_STEPS         default 4 (Schnell)
"""

from __future__ import annotations

import argparse
import base64
import io
import os
import sys
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1536


class GenerateBody(BaseModel):
    prompt: str = Field(min_length=1)
    model: str | None = None
    size: str | None = None
    n: int = 1
    response_format: str | None = "b64_json"
    width: int | None = None
    height: int | None = None
    steps: int | None = None


def _parse_size(size: str | None, width: int | None, height: int | None) -> tuple[int, int]:
    if width and height:
        return int(width), int(height)
    raw = (size or f"{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}").lower().replace(" ", "")
    try:
        w_s, h_s = raw.split("x", 1)
        return max(64, int(w_s)), max(64, int(h_s))
    except (TypeError, ValueError):
        return DEFAULT_WIDTH, DEFAULT_HEIGHT


def _allow_download() -> bool:
    return os.environ.get("FLUX_ALLOW_DOWNLOAD", "").strip() in {"1", "true", "yes"}


def _model_id() -> str:
    return os.environ.get("FLUX_MODEL_PATH") or os.environ.get("FLUX_MODEL") or DEFAULT_MODEL


def _missing_weights_message() -> str:
    return (
        "Flux Schnell weights are not on disk (~12 GB). This server will not download them "
        "unless you set FLUX_ALLOW_DOWNLOAD=1. Either download once with that flag, or set "
        "FLUX_MODEL_PATH to a local snapshot of black-forest-labs/FLUX.1-schnell. "
        "On this Intel Mac the 4 GB AMD GPU cannot hold Flux; inference will use CPU and "
        "take several minutes per 1024x1536 slide."
    )


@lru_cache(maxsize=1)
def _pipeline():
    try:
        import torch
        from diffusers import FluxPipeline
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Missing Python deps. From the repo root: "
                "python3 -m venv .venv-flux && source .venv-flux/bin/activate && "
                f"pip install -r scripts/requirements-flux.txt ({exc})"
            ),
        ) from exc

    model_id = _model_id()
    allow = _allow_download()
    if torch.cuda.is_available():
        device, dtype = "cuda", torch.bfloat16
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        device, dtype = "mps", torch.bfloat16
    else:
        device, dtype = "cpu", torch.float32

    try:
        pipe = FluxPipeline.from_pretrained(
            model_id,
            torch_dtype=dtype,
            local_files_only=not allow,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"{_missing_weights_message()} ({exc!s})"[:800]) from exc
    pipe = pipe.to(device)
    return pipe, device


def _run_generate(prompt: str, width: int, height: int, steps: int) -> bytes:
    pipe, _device = _pipeline()
    # Schnell is distilled; guidance_scale=0 is the published setting.
    image = pipe(
        prompt,
        width=width,
        height=height,
        guidance_scale=0.0,
        num_inference_steps=max(1, steps),
        max_sequence_length=256,
    ).images[0]
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


app = FastAPI(title="OpenLivery Flux Schnell sidecar", version="0.1.0")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": _model_id(),
        "allow_download": _allow_download(),
        "loaded": _pipeline.cache_info().currsize > 0,
    }


@app.get("/v1/models")
def list_models():
    return {"data": [{"id": "flux-schnell", "object": "model"}]}


@app.post("/generate")
@app.post("/v1/images/generations")
def generate(body: GenerateBody):
    width, height = _parse_size(body.size, body.width, body.height)
    # Align to 16 px, Flux requirement.
    width = max(64, (width // 16) * 16)
    height = max(64, (height // 16) * 16)
    steps = body.steps or int(os.environ.get("FLUX_STEPS") or 4)
    png = _run_generate(body.prompt, width, height, steps)
    b64 = base64.b64encode(png).decode("ascii")
    return {
        "created": 0,
        "data": [{"b64_json": b64}],
        "model": "flux-schnell",
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenLivery Flux Schnell sidecar")
    parser.add_argument("--host", default=os.environ.get("FLUX_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("FLUX_PORT", "7868")))
    parser.add_argument("--preload", action="store_true", help="Load weights at startup")
    args = parser.parse_args()
    if args.preload:
        try:
            _pipeline()
        except HTTPException as exc:
            print(exc.detail, file=sys.stderr)
            sys.exit(1)
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
