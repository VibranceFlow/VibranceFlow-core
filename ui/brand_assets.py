"""Brand icons from ui/Logos."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

_LOGOS = Path(__file__).resolve().parent / "Logos"
_ICO_DIR = _LOGOS / "ICO"
_PNG_DIR = _LOGOS / "PNG"


def ico_path() -> Path | None:
    for name in ("VibranceFlow.ico", "icon.ico"):
        p = _ICO_DIR / name
        if p.is_file():
            return p
    for p in _ICO_DIR.glob("*.ico"):
        return p
    for p in _LOGOS.glob("*.ico"):
        return p
    return None


def header_png_path() -> Path | None:
    for name in ("VibranceFlow.png", "logo.png", "icon.png"):
        p = _PNG_DIR / name
        if p.is_file():
            return p
    for p in _PNG_DIR.glob("*.png"):
        return p
    for p in _LOGOS.glob("*.png"):
        return p
    return None


def load_tray_image() -> Image.Image:
    path = header_png_path() or ico_path()
    if path and path.suffix.lower() == ".png":
        img = Image.open(path).convert("RGBA")
        return img.resize((64, 64), Image.Resampling.LANCZOS)
    if path and path.suffix.lower() == ".ico":
        img = Image.open(path)
        return img.convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
    return _fallback_icon()


def load_header_ctk_image(size: tuple[int, int] = (28, 28)):
    import customtkinter as ctk

    path = header_png_path()
    if not path:
        return None
    pil = Image.open(path).convert("RGBA")
    pil = pil.resize(size, Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=pil, dark_image=pil, size=size)


def _fallback_icon() -> Image.Image:
    from PIL import ImageDraw

    img = Image.new("RGBA", (64, 64), (10, 10, 15, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse((10, 10, 54, 54), fill=(0, 229, 192, 255))
    draw.ellipse((26, 26, 38, 38), fill=(139, 92, 246, 255))
    return img
