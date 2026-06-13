"""Pairing dialog: LAN IP + 6-digit code + QR (server must be listening)."""

from __future__ import annotations

import json

import customtkinter as ctk
import qrcode
from PIL import Image

from core.remote.firewall import is_firewall_configured, request_elevated_firewall_rule
from core.remote.pairing import DEFAULT_PORT, get_lan_ipv4_candidates
from core.remote.server import RemoteServer
from ui.app_context import VibranceFlowAppContext
from ui.layout import center_toplevel, compute_pairing_dialog_layout
from ui.modal_utils import activate_modal, bind_modal_close, destroy_modal
from ui.theme import ACCENT, BG_CARD, BG_DARK, FONT_SMALL, TEXT_MUTED, TEXT_PRIMARY
from ui.window_chrome import apply_windowed_chrome

_PAD = 10
_FOOTER_PAD = 6


class PairingDialog(ctk.CTkToplevel):
    def __init__(self, parent: ctk.CTk, ctx: VibranceFlowAppContext, server: RemoteServer) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._server = server
        self._qr_image: ctk.CTkImage | None = None
        self._qr_pil: Image.Image | None = None
        self._wait_label: ctk.CTkLabel | None = None
        self._pin_label: ctk.CTkLabel | None = None
        self._qr_label: ctk.CTkLabel | None = None
        self._fw_warn_label: ctk.CTkLabel | None = None
        self._fw_actions: ctk.CTkFrame | None = None
        self._qr_px = 148
        self._payload: dict = {}
        self._dialog_w = 400
        self._max_dialog_h = 640

        if not ctx.remote_is_listening:
            raise RuntimeError(
                ctx.remote_last_error or "Remote server is not listening. See app.log for details."
            )

        self.title("Pair Mobile")
        self.configure(fg_color=BG_DARK)

        fw_warn = ctx.consume_firewall_warning()
        host = server.host
        host_warn = host in ("127.0.0.1", "localhost")
        extra_warns = int(fw_warn is not None) + int(host_warn)

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self._dialog_w, self._max_dialog_h, self._qr_px = compute_pairing_dialog_layout(
            sw, sh, extra_warn_lines=extra_warns
        )

        apply_windowed_chrome(self, resizable=False)
        self.minsize(self._dialog_w, 320)
        self.maxsize(self._dialog_w, self._max_dialog_h)

        ctx.clear_pairing_complete_callbacks()
        ctx.on_pairing_complete(self._close_on_paired)

        outer = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        outer.pack(fill="both", expand=True, padx=_PAD, pady=_PAD)

        self._body_slot = ctk.CTkFrame(outer, fg_color=BG_DARK, corner_radius=0)
        self._body_slot.pack(fill="x", expand=False)

        self._footer = ctk.CTkFrame(outer, fg_color=BG_DARK, corner_radius=0)
        self._footer.pack(fill="x", pady=(_FOOTER_PAD, 0))
        self._build_footer(self._footer)

        self._mount_body(
            host=host,
            pin=server.pairing_pin,
            payload=server.pairing_payload,
            firewall_warn=fw_warn,
            host_warn=host_warn,
        )

        bind_modal_close(self, self._close)
        activate_modal(self, parent)
        self._status_tick()

    def _mount_body(
        self,
        *,
        host: str,
        pin: str,
        payload: dict,
        firewall_warn: str | None,
        host_warn: bool,
    ) -> None:
        for child in self._body_slot.winfo_children():
            child.destroy()

        plain = ctk.CTkFrame(self._body_slot, fg_color=BG_DARK, corner_radius=0)
        plain.pack(fill="x", expand=False)
        self._build_content(plain, host, pin, payload, firewall_warn, host_warn)
        self.update_idletasks()

        footer_h = self._footer.winfo_reqheight() + _FOOTER_PAD
        chrome_h = _PAD * 2 + footer_h + 28
        content_h = plain.winfo_reqheight()
        natural_h = content_h + chrome_h

        if natural_h <= self._max_dialog_h:
            center_toplevel(self, self._dialog_w, natural_h)
            return

        plain.destroy()
        scroll_h = self._max_dialog_h - chrome_h
        scroll = ctk.CTkScrollableFrame(
            self._body_slot,
            fg_color=BG_DARK,
            width=self._dialog_w - _PAD * 2 - 6,
            height=max(240, scroll_h),
            corner_radius=0,
        )
        scroll.pack(fill="x", expand=False)
        self._build_content(scroll, host, pin, payload, firewall_warn, host_warn)
        center_toplevel(self, self._dialog_w, self._max_dialog_h)

    def _close_on_paired(self) -> None:
        if not self.winfo_exists():
            return
        self._ctx.clear_pairing_complete_callbacks()
        destroy_modal(self)

    def _close(self) -> None:
        self._ctx.clear_pairing_complete_callbacks()
        if not self._ctx.profiles.settings.keep_remote_port_open:
            if self._ctx.remote_client_count == 0:
                self._ctx.stop_remote_server()
        destroy_modal(self)

    def _build_content(
        self,
        parent: ctk.CTkFrame | ctk.CTkScrollableFrame,
        host: str,
        pin: str,
        payload: dict,
        firewall_warn: str | None,
        host_warn: bool,
    ) -> None:
        wrap = self._dialog_w - 72
        box = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=10)
        box.pack(fill="x", padx=1, pady=1)

        ctk.CTkLabel(
            box,
            text="Pair VibranceFlow Mobile",
            font=("Segoe UI", 14, "bold"),
            text_color=ACCENT,
        ).pack(pady=(10, 2))

        ctk.CTkLabel(
            box,
            text=f"Listening on {host}:{DEFAULT_PORT} — same Wi‑Fi / LAN.",
            font=FONT_SMALL,
            text_color="#3fb950",
            justify="center",
            wraplength=wrap,
        ).pack(pady=(0, 4))

        self._wait_label = ctk.CTkLabel(
            box,
            text="Waiting for phone — scan QR or enter the code in the app.",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            justify="center",
            wraplength=wrap,
        )
        self._wait_label.pack(pady=(0, 4))

        if firewall_warn or not is_firewall_configured():
            self._fw_warn_label = ctk.CTkLabel(
                box,
                text=firewall_warn
                or (
                    f"Allow inbound TCP {DEFAULT_PORT} on private networks so the phone can connect."
                ),
                font=FONT_SMALL,
                text_color="#d29922",
                justify="center",
                wraplength=wrap,
            )
            self._fw_warn_label.pack(pady=(0, 4))
            self._fw_actions = ctk.CTkFrame(box, fg_color="transparent")
            self._fw_actions.pack(pady=(0, 4))
            ctk.CTkButton(
                self._fw_actions,
                text="Allow in Firewall",
                width=140,
                height=26,
                font=FONT_SMALL,
                command=self._on_allow_firewall,
            ).pack(side="left", padx=4)

        if host_warn:
            others = [ip for ip in get_lan_ipv4_candidates() if ip != host]
            hint = ", ".join(others[:3]) if others else "check Wi‑Fi / Ethernet"
            ctk.CTkLabel(
                box,
                text=f"WARNING: {host} is not reachable from the phone. Try: {hint}",
                font=FONT_SMALL,
                text_color="#f85149",
                justify="center",
                wraplength=wrap,
            ).pack(pady=(0, 4))

        creds = ctk.CTkFrame(box, fg_color="#161b22", corner_radius=8)
        creds.pack(fill="x", padx=12, pady=(2, 4))

        ip_block = ctk.CTkFrame(creds, fg_color="transparent")
        ip_block.pack(fill="x", padx=12, pady=(8, 2))
        ctk.CTkLabel(ip_block, text="IP on phone", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w")
        ctk.CTkLabel(
            ip_block,
            text=host,
            font=("Consolas", 22, "bold"),
            text_color=TEXT_PRIMARY if not host_warn else "#f85149",
        ).pack(anchor="w")

        pin_block = ctk.CTkFrame(creds, fg_color="transparent")
        pin_block.pack(fill="x", padx=12, pady=(4, 8))
        ctk.CTkLabel(pin_block, text="6-digit code", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w")
        pin_display = f"{pin[:3]} {pin[3:]}" if len(pin) == 6 else pin
        self._pin_label = ctk.CTkLabel(
            pin_block,
            text=pin_display,
            font=("Consolas", 26, "bold"),
            text_color=ACCENT,
        )
        self._pin_label.pack(anchor="w")

        ctk.CTkLabel(
            box,
            text="Code expires in ~15 min",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        ).pack(pady=(2, 2))

        ctk.CTkLabel(
            box,
            text="Or scan QR",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        ).pack(pady=(0, 2))

        qr_px = self._qr_px
        qr_pad = 10
        qr_frame = ctk.CTkFrame(
            box,
            fg_color="white",
            corner_radius=6,
            width=qr_px + qr_pad * 2,
            height=qr_px + qr_pad * 2,
        )
        qr_frame.pack(pady=(0, 10))
        qr_frame.pack_propagate(False)

        self._qr_label = ctk.CTkLabel(qr_frame, text="")
        self._qr_label.pack(expand=True)

        self._payload = payload
        self._set_qr(payload)

    def _build_footer(self, footer: ctk.CTkFrame) -> None:
        row = ctk.CTkFrame(footer, fg_color="transparent")
        row.pack()
        ctk.CTkButton(
            row, text="New code", width=96, height=26, font=FONT_SMALL, command=self._on_regenerate
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            row, text="Copy JSON", width=96, height=26, font=FONT_SMALL, command=self._on_copy_json
        ).pack(side="left", padx=3)
        ctk.CTkButton(row, text="Close", width=76, height=26, font=FONT_SMALL, command=self._close).pack(
            side="left", padx=3
        )

    def _status_tick(self) -> None:
        if not self.winfo_exists() or self._wait_label is None:
            return
        n = self._ctx.remote_client_count
        if n > 0:
            self._wait_label.configure(
                text=f"Phone connected ({n}). You can close this dialog.",
                text_color="#3fb950",
            )
        elif self._ctx.remote_is_listening:
            self._wait_label.configure(
                text="Waiting for phone — scan QR or enter the code in the app.",
                text_color=TEXT_MUTED,
            )
        else:
            self._wait_label.configure(
                text="Remote server stopped. Close and open Pair Mobile again.",
                text_color="#f85149",
            )
        self.after(1000, self._status_tick)

    def _set_qr(self, payload: dict) -> None:
        if self._qr_label is None:
            return
        text = json.dumps(payload, separators=(",", ":"))
        qr = qrcode.QRCode(box_size=4, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        px = self._qr_px
        self._qr_pil = img.resize((px, px), Image.Resampling.NEAREST)
        self._qr_image = ctk.CTkImage(
            light_image=self._qr_pil,
            dark_image=self._qr_pil,
            size=(px, px),
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
        try:
            self._ctx.regenerate_pairing_key()
        except Exception as e:
            messagebox.showerror(
                "New code",
                f"Could not rotate the pairing key:\n{e}",
                parent=self,
            )
            return
        server = self._ctx.ensure_remote_server()
        pin = server.pairing_pin
        pin_display = f"{pin[:3]} {pin[3:]}" if len(pin) == 6 else pin
        if self._pin_label is not None:
            self._pin_label.configure(text=pin_display)
        self._payload = self._ctx.pairing_payload
        self._set_qr(self._payload)

    def _on_copy_json(self) -> None:
        text = json.dumps(self._ctx.pairing_payload, indent=2)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

    def _on_allow_firewall(self) -> None:
        from tkinter import messagebox

        if is_firewall_configured():
            self._set_firewall_ok()
            return
        if self._fw_warn_label is not None:
            self._fw_warn_label.configure(text="Approve the Windows UAC prompt…")
        launched, err = request_elevated_firewall_rule(DEFAULT_PORT)
        if not launched:
            if self._fw_warn_label is not None and err:
                self._fw_warn_label.configure(text=err)
            if err:
                messagebox.showwarning("Firewall", err, parent=self)
            return
        self._poll_firewall_rule(0)

    def _poll_firewall_rule(self, attempt: int) -> None:
        if not self.winfo_exists():
            return
        if is_firewall_configured():
            self._set_firewall_ok()
            return
        if attempt >= 40:
            if self._fw_warn_label is not None:
                self._fw_warn_label.configure(
                    text=(
                        f"Rule not detected yet. Allow TCP {DEFAULT_PORT} on private networks "
                        "in Windows Firewall, or try again."
                    )
                )
            return
        self.after(500, lambda: self._poll_firewall_rule(attempt + 1))

    def _set_firewall_ok(self) -> None:
        if self._fw_warn_label is not None:
            self._fw_warn_label.configure(
                text=f"Firewall allowed TCP {DEFAULT_PORT} on private networks.",
                text_color="#3fb950",
            )
        if self._fw_actions is not None:
            self._fw_actions.destroy()
            self._fw_actions = None
