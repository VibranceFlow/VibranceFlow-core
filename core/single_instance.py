"""Prevent multiple GUI instances from competing for the same remote port."""

from __future__ import annotations

import atexit
import logging
import sys

logger = logging.getLogger(__name__)

_MUTEX_NAME = "Global\\VibranceFlow"
_lock_handle: int | None = None


def acquire_single_instance() -> bool:
    """Return False if another VibranceFlow instance is already running."""
    global _lock_handle
    if sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        ERROR_ALREADY_EXISTS = 183
        _lock_handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            logger.warning("Another VibranceFlow instance is already running")
            return False
        atexit.register(release_single_instance)
        return True

    # Portable fallback: PID lock file (Linux/macOS future builds).
    return True


def release_single_instance() -> None:
    global _lock_handle
    if sys.platform == "win32" and _lock_handle:
        import ctypes

        ctypes.windll.kernel32.CloseHandle(_lock_handle)
        _lock_handle = None


def show_already_running_message() -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "VibranceFlow",
            "VibranceFlow is already running.\n\n"
            "Close the other window or check the system tray.",
            parent=root,
        )
        root.destroy()
    except Exception:
        pass
