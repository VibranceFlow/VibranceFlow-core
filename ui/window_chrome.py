"""Platform window chrome helpers (non-maximizable windowed mode)."""

from __future__ import annotations

import sys

import customtkinter as ctk


def disable_maximize_button(window: ctk.CTk | ctk.CTkToplevel) -> None:
    """Remove the maximize button; keep resizable flag controlled by the caller."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(window.winfo_id()) or window.winfo_id()
        gwl_style = -16
        ws_maximizebox = 0x00010000
        style = user32.GetWindowLongW(hwnd, gwl_style)
        user32.SetWindowLongW(hwnd, gwl_style, style & ~ws_maximizebox)
    except Exception:
        pass


def apply_windowed_chrome(window: ctk.CTk | ctk.CTkToplevel, *, resizable: bool = False) -> None:
    window.resizable(resizable, resizable)
    window.after(20, lambda: disable_maximize_button(window))
