#!/usr/bin/env python3
"""Generate legacy placeholder PNG/ICO (teal ring + purple dot).

The product mark is ui/Logos/PNG/app_logo.png and ui/Logos/ICO/app_logo.ico.
This script only refreshes logo.png / logo.ico fallbacks — not the header/tray icon.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
PNG_DIR = ROOT / "ui" / "Logos" / "PNG"
ICO_DIR = ROOT / "ui" / "Logos" / "ICO"

BG = (10, 10, 15, 255)
RING = (0, 229, 192, 255)
CORE = (139, 92, 246, 255)
ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def render_logo(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), BG)
    draw = ImageDraw.Draw(img)
    margin = max(2, size // 8)
    outer = (margin, margin, size - margin - 1, size - margin - 1)
    draw.ellipse(outer, fill=RING)
    inner_margin = size // 4
    inner = (inner_margin, inner_margin, size - inner_margin - 1, size - inner_margin - 1)
    draw.ellipse(inner, fill=CORE)
    return img


def main() -> None:
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    ICO_DIR.mkdir(parents=True, exist_ok=True)

    png_path = PNG_DIR / "logo.png"
    render_logo(256).save(png_path, format="PNG")
    print(f"Wrote {png_path.relative_to(ROOT)}")

    ico_path = ICO_DIR / "logo.ico"
    base = render_logo(256)
    base.save(ico_path, format="ICO", sizes=ICO_SIZES)
    print(f"Wrote {ico_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
