"""Window sizing from screen resolution."""

from __future__ import annotations


def compute_window_sizes(screen_w: int, screen_h: int) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return (compact_w, compact_h), (expanded_w, expanded_h)."""
    compact_w = max(480, min(640, int(screen_w * 0.38)))
    compact_h = max(320, min(420, int(screen_h * 0.42)))
    expanded_h = max(560, min(compact_h + 260, int(screen_h * 0.78)))
    return (compact_w, compact_h), (compact_w, expanded_h)


def center_on_screen(window, width: int, height: int) -> None:
    window.update_idletasks()
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    x = max(0, (sw - width) // 2)
    y = max(0, (sh - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def parse_geometry(geo: str) -> tuple[int, int, int | None, int | None]:
    """Parse 'WxH+X+Y' into width, height, optional x, y."""
    import re

    m = re.match(r"(\d+)x(\d+)(?:\+(-?\d+)\+(-?\d+))?", geo.strip())
    if not m:
        return 520, 380, None, None
    w, h = int(m.group(1)), int(m.group(2))
    x = int(m.group(3)) if m.group(3) is not None else None
    y = int(m.group(4)) if m.group(4) is not None else None
    return w, h, x, y


def compute_pairing_dialog_layout(
    screen_w: int,
    screen_h: int,
    *,
    extra_warn_lines: int = 0,
) -> tuple[int, int, int]:
    """
    Return dialog width, max total height, and QR pixel size.

    Max height caps the window on large monitors; content is measured after build.
    """
    dialog_w = max(380, min(440, screen_w - 40))
    max_dialog_h = min(int(screen_h * 0.82), screen_h - 36)
    text_budget = 340 + extra_warn_lines * 34
    qr_px = max(120, min(160, max_dialog_h - text_budget - 108))
    return dialog_w, max_dialog_h, qr_px


def center_toplevel(window, width: int, height: int) -> None:
    window.update_idletasks()
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    x = max(8, (sw - width) // 2)
    y = max(8, (sh - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def set_window_size_keep_position(window, width: int, height: int) -> None:
    """Resize without re-centering if the window already has a position."""
    window.update_idletasks()
    _, _, x, y = parse_geometry(window.geometry())
    if x is not None and y is not None:
        window.geometry(f"{width}x{height}+{x}+{y}")
    else:
        center_on_screen(window, width, height)
