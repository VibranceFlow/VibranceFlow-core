"""Safe modal grab/focus helpers for CTkToplevel dialogs."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk


def release_modal_grab(window: tk.Misc) -> None:
    try:
        window.grab_release()
    except tk.TclError:
        pass


def activate_modal(dialog: ctk.CTkToplevel, master: ctk.CTk) -> None:
    """Show dialog and take grab only after it is visible (avoids stuck main window)."""
    dialog.transient(master)
    dialog.update_idletasks()
    try:
        dialog.deiconify()
    except tk.TclError:
        pass
    dialog.lift(master)
    dialog.attributes("-topmost", True)
    dialog.after(80, lambda: dialog.attributes("-topmost", False))
    dialog.focus_force()
    try:
        dialog.wait_visibility()
    except tk.TclError:
        pass
    dialog.grab_set()


def bind_modal_close(dialog: ctk.CTkToplevel, on_close=None) -> None:
    def _close() -> None:
        release_modal_grab(dialog)
        if on_close:
            on_close()
        else:
            dialog.destroy()

    dialog.protocol("WM_DELETE_WINDOW", _close)


def destroy_modal(dialog: ctk.CTkToplevel) -> None:
    release_modal_grab(dialog)
    try:
        dialog.destroy()
    except tk.TclError:
        pass


def release_all_modal_grabs(root: ctk.CTk) -> None:
    release_modal_grab(root)
    for child in root.winfo_children():
        if isinstance(child, (ctk.CTkToplevel, tk.Toplevel)):
            release_modal_grab(child)
            try:
                child.destroy()
            except tk.TclError:
                pass
