"""Pairing dialog: LAN IP + 6-digit code + QR (server starts on Pair Mobile)."""



from __future__ import annotations



import json

import tkinter as tk



import customtkinter as ctk

import qrcode

from PIL import Image



from core.remote.pairing import DEFAULT_PORT, get_lan_ipv4_candidates

from ui.app_context import LuminaAppContext

from ui.modal_utils import activate_modal, bind_modal_close, destroy_modal

from ui.theme import ACCENT, BG_CARD, BG_DARK, FONT_SMALL, TEXT_MUTED, TEXT_PRIMARY



_DIALOG_W = 400

_DIALOG_H = 640

_QR_PX = 200





class PairingDialog(ctk.CTkToplevel):

    def __init__(self, parent: ctk.CTk, ctx: LuminaAppContext) -> None:

        super().__init__(parent)

        self._ctx = ctx

        self._qr_image: ctk.CTkImage | None = None

        self._qr_pil: Image.Image | None = None



        self.title("Pair Mobile")

        self.configure(fg_color=BG_DARK)

        self.resizable(False, False)

        self.geometry(f"{_DIALOG_W}x{_DIALOG_H}")

        self.minsize(_DIALOG_W, _DIALOG_H)

        self.maxsize(_DIALOG_W, _DIALOG_H)



        was_running = ctx.remote_is_running
        server = ctx.ensure_remote_server()
        ctx.refresh_pairing_pin()

        ctx.clear_pairing_complete_callbacks()

        ctx.on_pairing_complete(self._close_on_paired)

        fw_warn = ctx.consume_firewall_warning()
        if not was_running and fw_warn is None:
            ctx.activate_keep_remote_port()

        self._build(server.host, server.pairing_pin, server.pairing_payload, fw_warn)

        self._center(parent)

        bind_modal_close(self, self._close)

        activate_modal(self, parent)



    def _close_on_paired(self) -> None:
        """Phone paired (PIN or QR) — hide dialog but keep the server for the session."""
        if not self.winfo_exists():
            return
        self._ctx.clear_pairing_complete_callbacks()
        destroy_modal(self)

    def _close(self) -> None:
        """User closed the dialog — stop server only if setting off and no phone connected."""
        self._ctx.clear_pairing_complete_callbacks()
        if not self._ctx.profiles.settings.keep_remote_port_open:
            if self._ctx.remote_client_count == 0:
                self._ctx.stop_remote_server()
        destroy_modal(self)



    def _center(self, parent: ctk.CTk) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        max_h = max(520, min(_DIALOG_H, sh - 80))
        max_w = min(_DIALOG_W, sw - 40)

        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        x = max(12, min(px + max(0, (pw - max_w) // 2), sw - max_w - 12))
        y = max(12, min(py + max(0, (ph - max_h) // 2), sh - max_h - 56))

        self.geometry(f"{max_w}x{max_h}+{x}+{y}")
        self.minsize(max_w, max_h)
        self.maxsize(max_w, max_h)



    def _build(self, host: str, pin: str, payload: dict, firewall_warn: str | None) -> None:

        outer = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)

        outer.pack(fill="both", expand=True, padx=12, pady=12)



        box = ctk.CTkFrame(outer, fg_color=BG_CARD, corner_radius=10)

        box.pack(fill="both", expand=True, padx=4, pady=4)



        ctk.CTkLabel(

            box,

            text="Pair VibranceFlow Mobile",

            font=("Segoe UI", 15, "bold"),

            text_color=ACCENT,

        ).pack(pady=(14, 4))



        ctk.CTkLabel(

            box,

            text="On the phone type the IP and 6-digit code below.\n"

            f"Port {DEFAULT_PORT} is fixed — or scan the QR.",

            font=FONT_SMALL,

            text_color=TEXT_MUTED,

            justify="center",

        ).pack(pady=(0, 10))



        if firewall_warn:

            ctk.CTkLabel(

                box,

                text=firewall_warn,

                font=FONT_SMALL,

                text_color="#d29922",

                justify="center",

                wraplength=_DIALOG_W - 80,

            ).pack(pady=(0, 8))



        host_warn = host in ("127.0.0.1", "localhost")

        if host_warn:

            others = [ip for ip in get_lan_ipv4_candidates() if ip != host]

            hint = ", ".join(others[:3]) if others else "check Wi‑Fi / Ethernet"

            ctk.CTkLabel(

                box,

                text=f"WARNING: {host} is not reachable from the phone.\nTry: {hint}",

                font=FONT_SMALL,

                text_color="#f85149",

                justify="center",

                wraplength=_DIALOG_W - 80,

            ).pack(pady=(0, 8))



        creds = ctk.CTkFrame(box, fg_color="#161b22", corner_radius=8)

        creds.pack(fill="x", padx=16, pady=4)



        ip_block = ctk.CTkFrame(creds, fg_color="transparent")

        ip_block.pack(fill="x", padx=14, pady=(12, 4))

        ctk.CTkLabel(

            ip_block,

            text="IP to enter on phone",

            font=FONT_SMALL,

            text_color=TEXT_MUTED,

        ).pack(anchor="w")

        ctk.CTkLabel(

            ip_block,

            text=host,

            font=("Consolas", 26, "bold"),

            text_color=TEXT_PRIMARY if not host_warn else "#f85149",

        ).pack(anchor="w")



        pin_block = ctk.CTkFrame(creds, fg_color="transparent")

        pin_block.pack(fill="x", padx=14, pady=(8, 12))

        ctk.CTkLabel(

            pin_block,

            text="6-digit code",

            font=FONT_SMALL,

            text_color=TEXT_MUTED,

        ).pack(anchor="w")

        pin_display = f"{pin[:3]} {pin[3:]}" if len(pin) == 6 else pin

        self._pin_label = ctk.CTkLabel(

            pin_block,

            text=pin_display,

            font=("Consolas", 32, "bold"),

            text_color=ACCENT,

        )

        self._pin_label.pack(anchor="w")



        ctk.CTkLabel(

            box,

            text="Code expires in ~15 min · same Wi‑Fi / LAN",

            font=FONT_SMALL,

            text_color=TEXT_MUTED,

        ).pack(pady=(6, 8))



        ctk.CTkLabel(

            box,

            text="Or scan QR (full pairing)",

            font=FONT_SMALL,

            text_color=TEXT_MUTED,

        ).pack(pady=(0, 4))



        qr_frame = ctk.CTkFrame(box, fg_color="white", corner_radius=8, width=_QR_PX + 16, height=_QR_PX + 16)

        qr_frame.pack(pady=4)

        qr_frame.pack_propagate(False)



        self._qr_label = ctk.CTkLabel(qr_frame, text="", width=_QR_PX, height=_QR_PX)

        self._qr_label.pack(expand=True)

        self._payload = payload

        self._set_qr(payload)



        row = ctk.CTkFrame(box, fg_color="transparent")

        row.pack(pady=(14, 14))

        ctk.CTkButton(

            row,

            text="New code",

            width=100,

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

        qr = qrcode.QRCode(box_size=4, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)

        qr.add_data(text)

        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        self._qr_pil = img.resize((_QR_PX, _QR_PX), Image.Resampling.NEAREST)

        self._qr_image = ctk.CTkImage(

            light_image=self._qr_pil,

            dark_image=self._qr_pil,

            size=(_QR_PX, _QR_PX),

        )

        self._qr_label.configure(image=self._qr_image, text="")



    def _on_regenerate(self) -> None:
        from tkinter import messagebox

        if not messagebox.askyesno(
            "New code",
            "This invalidates the current pairing key.\n\n"
            "Phones already connected must scan the new QR or enter the new code.\n\n"
            "Continue?",
            parent=self,
        ):
            return

        self._ctx.regenerate_pairing_key()

        server = self._ctx.ensure_remote_server()

        pin = server.pairing_pin

        pin_display = f"{pin[:3]} {pin[3:]}" if len(pin) == 6 else pin

        self._pin_label.configure(text=pin_display)

        self._payload = self._ctx.pairing_payload

        self._set_qr(self._payload)



    def _on_copy_json(self) -> None:

        payload = self._ctx.pairing_payload

        text = json.dumps(payload, indent=2)

        self.clipboard_clear()

        self.clipboard_append(text)

        self.update()


