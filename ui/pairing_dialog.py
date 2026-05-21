"""QR pairing dialog for mobile remote control."""

from __future__ import annotations

import io
import json
import tkinter as tk

import customtkinter as ctk
import qrcode
from PIL import Image

from ui.app_context import LuminaAppContext
from ui.modal_utils import activate_modal, bind_modal_close, destroy_modal
from ui.theme import ACCENT, BG_CARD, BG_DARK, FONT_SMALL, TEXT_MUTED, TEXT_PRIMARY


class PairingDialog(ctk.CTkToplevel):
    def __init__(self, parent: ctk.CTk, ctx: LuminaAppContext) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._qr_image: ctk.CTkImage | None = None

        self.title("Pair Mobile")
        self.configure(fg_color=BG_DARK)
        self.resizable(False, False)
        self.minsize(360, 420)
        self.maxsize(360, 420)
        server = ctx.ensure_remote_server()
        self._build(server.pairing_payload)
        self._center(parent)
        bind_modal_close(self, self._close)
        activate_modal(self, parent)

    def _close(self) -> None:
        destroy_modal(self)

    def _center(self, parent: ctk.CTk) -> None:
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        w, h = self.winfo_width(), self.winfo_height()
        x = px + max(0, (pw - w) // 2)
        y = py + max(0, (ph - h) // 2)
        self.geometry(f"+{x}+{y}")

    def _build(self, payload: dict) -> None:
        box = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        box.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            box,
            text="Scan with LuminaSync Mobile",
            font=("Segoe UI", 14, "bold"),
            text_color=ACCENT,
        ).pack(pady=(12, 4))

        host = payload.get("host", "?")
        port = payload.get("port", "?")
        ctk.CTkLabel(
            box,
            text=f"{host}:{port}  (LAN only)",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        ).pack(pady=(0, 8))

        self._qr_label = ctk.CTkLabel(box, text="")
        self._qr_label.pack(pady=8)
        self._set_qr(payload)

        ctk.CTkLabel(
            box,
            text="Traffic is encrypted with a one-time key in the QR.\n"
            "Only devices on your local network can reach this port.",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            justify="center",
        ).pack(pady=(4, 12))

        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(pady=(0, 12))
        ctk.CTkButton(
            row,
            text="Regenerate key",
            width=120,
            height=28,
            font=FONT_SMALL,
            command=self._on_regenerate,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            row,
            text="Copy JSON",
            width=100,
            height=28,
            font=FONT_SMALL,
            command=self._on_copy_json,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            row,
            text="Close",
            width=80,
            height=28,
            font=FONT_SMALL,
            command=self._close,
        ).pack(side="left", padx=4)

    def _set_qr(self, payload: dict) -> None:
        text = json.dumps(payload, separators=(",", ":"))
        qr = qrcode.QRCode(box_size=6, border=2)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        pil = img.resize((220, 220), Image.Resampling.NEAREST)
        self._qr_image = ctk.CTkImage(light_image=pil, dark_image=pil, size=(220, 220))
        self._qr_label.configure(image=self._qr_image, text="")

    def _on_regenerate(self) -> None:
        self._ctx.regenerate_pairing_key()
        self._set_qr(self._ctx.pairing_payload)

    def _on_copy_json(self) -> None:
        payload = self._ctx.pairing_payload
        text = json.dumps(payload, indent=2)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
