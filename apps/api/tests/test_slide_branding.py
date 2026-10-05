"""Real brand mark is composited; it is never invented by the image model."""

import io

from PIL import Image

from app.services.slide_branding import apply_brand_mark


def _solid_png(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def test_composites_uploaded_logo_top_left():
    photo = _solid_png(400, 500, (20, 80, 120))
    logo = _solid_png(80, 40, (255, 0, 0))
    out, mime = apply_brand_mark(photo, logo_bytes=logo, logo_mime="image/png", brand_name="Should Not Appear")
    assert mime == "image/png"
    img = Image.open(io.BytesIO(out)).convert("RGB")
    assert img.size == (400, 500)
    # Logo sits on a light plate near top-left, not the original teal.
    corner = img.getpixel((40, 40))
    assert corner[0] > 150
    # Center of the photo stays teal.
    mid = img.getpixel((200, 250))
    assert mid[2] > 80


def test_wordmark_fallback_when_logo_missing():
    photo = _solid_png(400, 500, (20, 80, 120))
    out, mime = apply_brand_mark(photo, logo_bytes=None, logo_mime=None, brand_name="La Casona")
    assert mime == "image/png"
    img = Image.open(io.BytesIO(out))
    assert img.size == (400, 500)
    corner = img.convert("RGB").getpixel((40, 40))
    assert corner[0] > 150
