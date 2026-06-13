"""Brand icons from ui/Logos (dev + Nuitka frozen)."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

_PNG_PREFERRED = (
    "app_logo.png",
    "final.png",
    "VibranceFlow.png",
    "logo.png",
    "icon.png",
)
_ICO_PREFERRED = (
    "app_logo.ico",
    "logo.ico",
    "VibranceFlow.ico",
    "icon.ico",
)


def logos_root() -> Path:
    """Resolve ui/Logos in source tree and Nuitka onefile/standalone builds."""
    candidates: list[Path] = []

    module_dir = Path(__file__).resolve().parent
    candidates.append(module_dir / "Logos")

    if getattr(sys, "frozen", False):
        onefile_dir = os.environ.get("NUITKA_ONEFILE_DIRECTORY")
        if onefile_dir:
            candidates.append(Path(onefile_dir) / "ui" / "Logos")
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / "ui" / "Logos")

    seen: set[Path] = set()
    for root in candidates:
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / "PNG").is_dir() or (resolved / "ICO").is_dir():
            return resolved

    return module_dir / "Logos"


def _first_in_dir(directory: Path, names: tuple[str, ...]) -> Path | None:
    if not directory.is_dir():
        return None
    for name in names:
        path = directory / name
        if path.is_file():
            return path
    return None


def ico_path() -> Path | None:
    root = logos_root()
    found = _first_in_dir(root / "ICO", _ICO_PREFERRED)
    if found:
        return found
    for path in sorted(root.glob("*.ico")):
        return path
    return None


def header_png_path() -> Path | None:
    root = logos_root()
    found = _first_in_dir(root / "PNG", _PNG_PREFERRED)
    if found:
        return found
    for path in sorted(root.glob("*.png")):
        return path
    return None


def load_tray_image() -> Image.Image:
    path = header_png_path() or ico_path()
    if path and path.suffix.lower() == ".png":
        img = Image.open(path).convert("RGBA")
        return img.resize((64, 64), Image.Resampling.LANCZOS)
    if path and path.suffix.lower() == ".ico":
        img = Image.open(path)
        return img.convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
    logger.warning("Brand icon not found under %s; using fallback", logos_root())
    return _fallback_icon()


def load_header_ctk_image(size: tuple[int, int] = (28, 28)):
    import customtkinter as ctk

    path = header_png_path()
    if not path:
        logger.warning("Header logo PNG not found under %s", logos_root())
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
