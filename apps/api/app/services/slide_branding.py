"""Composite the real client brand mark onto a generated slide. Never invent a logo."""

from __future__ import annotations

import io
import logging

from PIL import Image, ImageDraw, ImageFilter, ImageFont


logger = logging.getLogger(__name__)

RASTER_LOGO_MIMES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}


def apply_brand_mark(
    image_bytes: bytes,
    *,
    logo_bytes: bytes | None,
    logo_mime: str | None,
    brand_name: str,
) -> tuple[bytes, str]:
    """Paste the uploaded logo (or a typeset name) top-left. Returns PNG bytes."""
    canvas = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    mark = _load_logo(logo_bytes, logo_mime)
    if mark is None:
        mark = _wordmark(brand_name, canvas.size)
    if mark is None:
        return image_bytes, "image/png"
    placed = _place_top_left(canvas, mark)
    out = io.BytesIO()
    placed.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue(), "image/png"


def _load_logo(logo_bytes: bytes | None, logo_mime: str | None) -> Image.Image | None:
    if not logo_bytes:
        return None
    mime = (logo_mime or "").lower().split(";")[0].strip()
    if mime == "image/svg+xml" or logo_bytes.lstrip()[:4] == b"<svg" or logo_bytes.lstrip()[:5] == b"<?xml":
        return None
    if mime and mime not in RASTER_LOGO_MIMES and not logo_bytes.startswith(b"\x89PNG") and not logo_bytes.startswith(b"\xff\xd8"):
        return None
    try:
        logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
    except Exception as exc:  # noqa: BLE001
        logger.warning("brand logo could not be opened: %s", exc)
        return None
    if logo.width < 8 or logo.height < 8:
        return None
    return logo


def _wordmark(name: str, canvas_size: tuple[int, int]) -> Image.Image | None:
    text = (name or "").strip()
    if not text:
        return None
    width, height = canvas_size
    font_size = max(28, int(width * 0.038))
    font = _font(font_size)
    probe = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    draw = ImageDraw.Draw(probe)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = max(18, font_size // 2), max(10, font_size // 3)
    img = Image.new("RGBA", (tw + pad_x * 2, th + pad_y * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=14, fill=(255, 255, 255, 220))
    draw.text((pad_x - bbox[0], pad_y - bbox[1]), text, font=font, fill=(15, 23, 42, 255))
    max_w = int(width * 0.42)
    if img.width > max_w:
        ratio = max_w / img.width
        img = img.resize((max_w, max(1, int(img.height * ratio))), Image.Resampling.LANCZOS)
    return img


def _place_top_left(canvas: Image.Image, mark: Image.Image) -> Image.Image:
    width, height = canvas.size
    max_w = max(48, int(width * 0.22))
    max_h = max(32, int(height * 0.10))
    mw, mh = mark.size
    scale = min(max_w / mw, max_h / mh, 1.0)
    if scale < 1:
        mark = mark.resize((max(1, int(mw * scale)), max(1, int(mh * scale))), Image.Resampling.LANCZOS)
    pad = max(24, int(width * 0.045))
    plate = _plate_behind(mark)
    x, y = pad, pad
    shadow = plate.filter(ImageFilter.GaussianBlur(4))
    canvas.alpha_composite(shadow, (x + 2, y + 3))
    canvas.alpha_composite(plate, (x, y))
    return canvas


def _plate_behind(mark: Image.Image) -> Image.Image:
    pad = 10
    plate = Image.new("RGBA", (mark.width + pad * 2, mark.height + pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(plate)
    draw.rounded_rectangle((0, 0, plate.width - 1, plate.height - 1), radius=12, fill=(255, 255, 255, 200))
    plate.alpha_composite(mark, (pad, pad))
    return plate


def _font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()
