#!/usr/bin/env python3
"""Export Instagram carousel HTML slides to PNG (1080×1350)."""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SLIDES_DIR = Path(__file__).resolve().parents[1] / "slides"
OUT_DIR = Path(__file__).resolve().parents[1] / "export"


def export_html(html_path: Path) -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    url = html_path.resolve().as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        page.goto(url, wait_until="networkidle")
        slides = page.locator(".slide")
        count = slides.count()
        stem = html_path.stem
        target_dir = OUT_DIR / stem
        target_dir.mkdir(exist_ok=True)

        for i in range(count):
            slide = slides.nth(i)
            slide.scroll_into_view_if_needed()
            out = target_dir / f"{i + 1:02d}.png"
            slide.screenshot(path=str(out))
            saved.append(out)

        browser.close()
    return saved


def main() -> int:
    files = sorted(SLIDES_DIR.glob("carrusel-*.html"))
    if not files:
        print("No carousel HTML files found", file=sys.stderr)
        return 1

    all_saved: list[Path] = []
    for html in files:
        paths = export_html(html)
        all_saved.extend(paths)
        print(f"{html.name}: {len(paths)} slides → {OUT_DIR / html.stem}/")

    print(f"Total: {len(all_saved)} PNGs in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
