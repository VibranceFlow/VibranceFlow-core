"""VibranceFlow main window - compact layout."""

from __future__ import annotations

import tkinter.messagebox as messagebox

import customtkinter as ctk

from core.models import AudioSettings, ColorProfile
from ui.app_context import VibranceFlowAppContext
from ui.brand_assets import ico_path, load_header_ctk_image
from ui.layout import center_on_screen, compute_window_sizes, set_window_size_keep_position
from ui.window_chrome import apply_windowed_chrome
from ui.pairing_dialog import PairingDialog
from ui.process_picker import ProcessPickerDialog
from ui.theme import (
    ACCENT,
    ACCENT_SECONDARY,
    BG_CARD,
    BG_CARD_HOVER,
    BG_DARK,
    DANGER,
    FONT_SMALL,
    SUCCESS,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from ui.tray import TrayController
from ui.util import Debouncer
from ui.modal_utils import release_all_modal_grabs

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class VibranceFlowWindow(ctk.CTk):
    def __init__(self, ctx: VibranceFlowAppContext, *, start_hidden: bool = False) -> None:
        super().__init__()
        self._ctx = ctx
        self._selected_exe: str | None = None
        self._program_buttons: dict[str, ctk.CTkButton] = {}
        self._slider_vars: dict[str, ctk.DoubleVar | ctk.IntVar] = {}
        self._updating_sliders = False
        self._updating_audio = False
        self._audio_available = False
        self._audio_muted = False
        self._audio_var = ctk.DoubleVar(value=100.0)
        self._quitting = False
        self._visible = not start_hidden

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        _compact, self._size_expanded = compute_window_sizes(sw, sh)
        self._size_compact = self._size_expanded
        self._expanded = True

        self.title("VibranceFlow")
        self.configure(fg_color=BG_DARK)
        cw, ch = self._size_compact
        ew, eh = self._size_expanded
        apply_windowed_chrome(self, resizable=False)
        self.minsize(cw, ch)
        self.maxsize(ew, eh)
        self._apply_window_icon()

        self._build_header()
        self._build_settings()
        self._build_programs()
        self._build_profile_editor()
        self._build_status()

        self._profile_debouncer = Debouncer(self, 180, self._flush_profile_save)
        self._audio_debouncer = Debouncer(self, 180, self._flush_audio_save)
        self._desktop_debouncer = Debouncer(self, 180, self._flush_desktop_vibrance)

        self._tray = TrayController(on_show=self._show_from_tray, on_quit=self._quit_app)
        self._tray.start()

        self._refresh_program_grid()
        self._sync_desktop_sliders()
        self._hide_profile_panel()
        self._update_status()
        self._ctx.on_ui_sync(self._sync_from_context)

        self.protocol("WM_DELETE_WINDOW", self._on_close_attempt)
        self.bind("<Unmap>", self._on_unmap)

        self.after(50, self._finish_window_setup, start_hidden)

    def _apply_window_icon(self) -> None:
        path = ico_path()
        if path:
            try:
                self.iconbitmap(default=str(path))
            except Exception:
                pass

    def _finish_window_setup(self, start_hidden: bool) -> None:
        w, h = self._size_compact
        center_on_screen(self, w, h)
        if start_hidden:
            self.withdraw()
        else:
            self.after(1500, self._status_tick)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=44)
        header.pack(fill="x")
        header.pack_propagate(False)

        logo = load_header_ctk_image((28, 28))
        if logo:
            ctk.CTkLabel(header, image=logo, text="").pack(side="left", padx=(12, 4), pady=8)
        ctk.CTkLabel(
            header,
            text="VibranceFlow",
            font=("Segoe UI", 16, "bold"),
            text_color=ACCENT,
        ).pack(side="left", padx=(0, 8), pady=8)

    def _build_settings(self) -> None:
        box = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        box.pack(fill="x", padx=10, pady=(8, 4))

        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=6)
        s = self._ctx.profiles.settings

        self._chk_observer = ctk.CTkCheckBox(
            row,
            text="Observer",
            width=90,
            font=FONT_SMALL,
            fg_color=ACCENT,
            height=22,
            command=self._on_observer_toggle,
        )
        self._chk_observer.pack(side="left", padx=(0, 8))
        if s.observer_enabled:
            self._chk_observer.select()

        self._chk_autostart = ctk.CTkCheckBox(
            row,
            text="Start with Windows",
            width=130,
            font=FONT_SMALL,
            fg_color=ACCENT,
            height=22,
            command=self._on_autostart_toggle,
        )
        self._chk_autostart.pack(side="left")
        if s.autostart or self._ctx.sync_autostart_checkbox():
            self._chk_autostart.select()

        row_keep = ctk.CTkFrame(box, fg_color="transparent")
        row_keep.pack(fill="x", padx=8, pady=(0, 6))
        self._chk_keep_port = ctk.CTkCheckBox(
            row_keep,
            text="Keep remote port open (8765)",
            width=200,
            font=FONT_SMALL,
            fg_color=ACCENT,
            height=22,
            command=self._on_keep_port_toggle,
        )
        self._chk_keep_port.pack(side="left")
        self._updating_keep_port = False
        self._sync_keep_port_checkbox()

        ctk.CTkButton(
            row,
            text="Pair Mobile",
            width=88,
            height=24,
            font=FONT_SMALL,
            fg_color=ACCENT_SECONDARY,
            hover_color=ACCENT,
            text_color="white",
            command=self._on_pair_mobile,
        ).pack(side="right")

        row2 = ctk.CTkFrame(box, fg_color="transparent")
        row2.pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkLabel(
            row2,
            text="Vibrance desktop",
            font=FONT_SMALL,
            text_color=TEXT_SECONDARY,
        ).pack(side="left")
        self._lbl_desktop_v = ctk.CTkLabel(
            row2,
            text=f"{s.desktop_vibrance:.0f}%",
            font=FONT_SMALL,
            text_color=ACCENT,
            width=40,
        )
        self._lbl_desktop_v.pack(side="right")
        self._slider_desktop_v = ctk.CTkSlider(
            row2,
            from_=0,
            to=100,
            width=200,
            height=14,
            progress_color=ACCENT,
            button_color=ACCENT_SECONDARY,
            command=self._on_desktop_vibrance_slide,
        )
        self._slider_desktop_v.set(s.desktop_vibrance)
        self._slider_desktop_v.pack(side="right", padx=(8, 4))

    def _build_programs(self) -> None:
        box = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        box.pack(fill="x", padx=10, pady=4)

        top = ctk.CTkFrame(box, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(6, 4))
        ctk.CTkLabel(top, text="Programs", font=FONT_SMALL, text_color=TEXT_PRIMARY).pack(
            side="left"
        )
        for text, cmd, w, color in (
            ("+ Add", self._on_add_running, 56, ACCENT),
            ("Manual", self._on_add_manual, 56, ACCENT_SECONDARY),
            ("−", self._on_remove, 36, DANGER),
        ):
            ctk.CTkButton(
                top,
                text=text,
                width=w,
                height=24,
                font=FONT_SMALL,
                fg_color=color,
                hover_color=ACCENT,
                text_color=BG_DARK if color != DANGER else "white",
                command=cmd,
            ).pack(side="right", padx=2)

        self._programs_frame = ctk.CTkFrame(box, fg_color=BG_DARK, height=72)
        self._programs_frame.pack(fill="x", padx=6, pady=(0, 6))
        self._programs_frame.pack_propagate(True)

    def _build_profile_editor(self) -> None:
        self._profile_box = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        self._profile_inner = ctk.CTkFrame(self._profile_box, fg_color="transparent")
        self._editor_body = ctk.CTkFrame(self._profile_inner, fg_color="transparent")
        self._sliders_container = ctk.CTkFrame(self._editor_body, fg_color="transparent")

        title_row = ctk.CTkFrame(self._profile_inner, fg_color="transparent")
        title_row.pack(fill="x", padx=8, pady=(6, 2))
        self._profile_title = ctk.CTkLabel(
            title_row,
            text="",
            font=FONT_SMALL,
            text_color=ACCENT,
        )
        self._profile_title.pack(side="left")
        self._btn_reset = ctk.CTkButton(
            title_row,
            text="Reset",
            width=56,
            height=22,
            font=FONT_SMALL,
            fg_color=BG_CARD_HOVER,
            hover_color=DANGER,
            text_color=TEXT_PRIMARY,
            command=self._on_reset_profile,
        )
        self._btn_reset.pack(side="right")

        self._editor_body.pack(fill="x", padx=4, pady=(0, 8))
        self._sliders_container.pack(side="left", fill="x", expand=True)

        specs = [
            ("vibrance", "Vib", 0, 100, 100),
            ("brightness", "Bri", -50, 50, 100),
            ("contrast", "Con", -50, 50, 100),
            ("gamma", "Gam", 0.4, 2.8, 24),
            ("hue", "Hue", 0, 359, 359),
        ]
        for key, label, lo, hi, steps in specs:
            row = ctk.CTkFrame(self._sliders_container, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row,
                text=label,
                font=FONT_SMALL,
                text_color=TEXT_SECONDARY,
                width=32,
            ).pack(side="left")
            val_lbl = ctk.CTkLabel(row, text="—", font=FONT_SMALL, text_color=ACCENT, width=44)
            val_lbl.pack(side="right")
            var: ctk.DoubleVar | ctk.IntVar = (
                ctk.IntVar(value=0) if key == "hue" else ctk.DoubleVar(value=0.0)
            )
            self._slider_vars[key] = var
            ctk.CTkSlider(
                row,
                from_=lo,
                to=hi,
                number_of_steps=int(steps),
                height=16,
                variable=var,
                progress_color=ACCENT_SECONDARY,
                command=lambda _v, k=key: self._on_profile_slider_move(k),
            ).pack(side="left", fill="x", expand=True, padx=4)
            setattr(self, f"_lbl_{key}", val_lbl)

        self._audio_side = ctk.CTkFrame(self._editor_body, fg_color=BG_DARK, corner_radius=8, width=88)
        self._audio_side.pack(side="right", fill="y", padx=(10, 0))
        self._audio_side.pack_propagate(False)
        ctk.CTkLabel(
            self._audio_side,
            text="Audio",
            font=FONT_SMALL,
            text_color=TEXT_SECONDARY,
        ).pack(pady=(10, 6))
        self._btn_audio_mute = ctk.CTkButton(
            self._audio_side,
            text="🔊",
            width=40,
            height=32,
            font=FONT_SMALL,
            fg_color=BG_CARD_HOVER,
            hover_color=ACCENT,
            text_color=TEXT_PRIMARY,
            command=self._on_audio_mute_toggle,
        )
        self._btn_audio_mute.pack(pady=(0, 8))
        self._audio_slider = ctk.CTkSlider(
            self._audio_side,
            from_=0,
            to=100,
            number_of_steps=100,
            width=18,
            height=148,
            variable=self._audio_var,
            progress_color=ACCENT_SECONDARY,
            button_color=ACCENT,
            command=self._on_audio_slide,
            orientation="vertical",
        )
        self._audio_slider.pack(pady=(0, 8))
        self._lbl_audio = ctk.CTkLabel(
            self._audio_side,
            text="100%",
            font=("Segoe UI", 13, "bold"),
            text_color=ACCENT,
        )
        self._lbl_audio.pack(pady=(0, 6))
        self._audio_hint = ctk.CTkLabel(
            self._audio_side,
            text="",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            wraplength=72,
            justify="center",
        )
        self._audio_hint.pack(fill="x", padx=6, pady=(0, 10))

    def _build_status(self) -> None:
        self._status_bar = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=28)
        self._status_bar.pack(fill="x", side="bottom")
        self._status_bar.pack_propagate(False)
        self._status_label = ctk.CTkLabel(
            self._status_bar,
            text="",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        )
        self._status_label.pack(side="left", padx=10)
        self._engine_label = ctk.CTkLabel(self._status_bar, text="", font=FONT_SMALL)
        self._engine_label.pack(side="right", padx=10)

    def _profile_panel_visible(self) -> bool:
        try:
            return bool(self._profile_box.winfo_ismapped())
        except tk.TclError:
            return False

    def _hide_profile_panel(self) -> None:
        if self._profile_panel_visible():
            self._profile_box.pack_forget()
        if self._expanded:
            self._set_window_expanded(False)

    def _show_profile_panel(self, exe: str) -> None:
        need_resize = not self._expanded
        if not self._profile_panel_visible():
            self._profile_box.pack(fill="x", padx=10, pady=(4, 6), before=self._status_bar)
            self._profile_inner.pack(fill="x", padx=4, pady=4)
        self._profile_title.configure(text=exe)
        if need_resize:
            self._set_window_expanded(True)

    def _set_window_expanded(self, expanded: bool) -> None:
        if expanded == self._expanded:
            return
        self._expanded = expanded
        w, h = self._size_expanded if expanded else self._size_compact
        set_window_size_keep_position(self, w, h)

    def _refresh_program_grid(self) -> None:
        for w in self._programs_frame.winfo_children():
            w.destroy()
        self._program_buttons.clear()

        exes = self._ctx.profiles.list_executables()
        if not exes:
            ctk.CTkLabel(
                self._programs_frame,
                text="(empty)",
                font=FONT_SMALL,
                text_color=TEXT_MUTED,
            ).pack(padx=8, pady=8)
            return

        inner = ctk.CTkFrame(self._programs_frame, fg_color="transparent")
        inner.pack(fill="x", anchor="w")

        for exe in exes:
            short = exe.replace(".exe", "")[:10]
            sel = exe == self._selected_exe
            btn = ctk.CTkButton(
                inner,
                text=short,
                width=72,
                height=26,
                corner_radius=6,
                font=FONT_SMALL,
                fg_color=ACCENT if sel else BG_CARD_HOVER,
                hover_color=ACCENT,
                text_color=BG_DARK if sel else TEXT_PRIMARY,
                command=lambda e=exe: self._select_program(e),
            )
            btn.pack(side="left", padx=3, pady=6)
            self._program_buttons[exe] = btn

    def _select_program(self, exe: str) -> None:
        self._selected_exe = exe
        for name, btn in self._program_buttons.items():
            sel = name == exe
            btn.configure(
                fg_color=ACCENT if sel else BG_CARD_HOVER,
                text_color=BG_DARK if sel else TEXT_PRIMARY,
            )
        profile = self._ctx.profiles.get(exe)
        if not profile:
            return
        self._show_profile_panel(exe)
        self._updating_sliders = True
        self._slider_vars["vibrance"].set(profile.vibrance)
        self._slider_vars["brightness"].set(profile.brightness)
        self._slider_vars["contrast"].set(profile.contrast)
        self._slider_vars["gamma"].set(profile.gamma)
        self._slider_vars["hue"].set(profile.hue)
        self._updating_sliders = False
        self._refresh_slider_labels()
        self._apply_audio_state(exe)

    def _clear_program_selection(self) -> None:
        self._selected_exe = None
        self._hide_profile_panel()
        self._refresh_program_grid()

    def _on_reset_profile(self) -> None:
        if not self._selected_exe:
            return
        exe = self._selected_exe
        if not messagebox.askyesno(
            "Reset profile",
            f"Reset color profile for {exe} to GPU defaults captured at startup?",
            parent=self,
        ):
            return
        self._ctx.reset_program_to_gpu_default(exe)
        self._select_program(exe)

    def _on_pair_mobile(self) -> None:
        try:
            if self._ctx.remote_is_listening and self._ctx.remote_client_count > 0:
                if messagebox.askyesno(
                    "Pair Mobile",
                    "A phone is already connected.\n\n"
                    "Disconnect it and show a new QR / pairing code?\n"
                    "(The phone must scan the new QR or enter the new code.)",
                    parent=self,
                ):
                    self._ctx.disconnect_remote_clients(rotate_key=True)
            server = self._ctx.prepare_pairing_session(persist_keep_port=True)
            PairingDialog(self, self._ctx, server)
        except Exception as e:
            messagebox.showerror("Pair Mobile", str(e), parent=self)

    def _refresh_slider_labels(self) -> None:
        if not self._selected_exe:
            return
        self._lbl_vibrance.configure(text=f"{self._slider_vars['vibrance'].get():.0f}%")
        self._lbl_brightness.configure(text=f"{self._slider_vars['brightness'].get():+.0f}%")
        self._lbl_contrast.configure(text=f"{self._slider_vars['contrast'].get():+.0f}%")
        self._lbl_gamma.configure(text=f"{self._slider_vars['gamma'].get():.2f}")
        self._lbl_hue.configure(text=f"{int(self._slider_vars['hue'].get())}°")
        self._lbl_audio.configure(text=f"{self._audio_var.get():.0f}%")

    def _apply_audio_state(self, exe: str) -> None:
        state = self._ctx.get_program_audio_state(exe)
        self._audio_available = state.available
        self._audio_muted = state.muted
        self._updating_audio = True
        self._audio_var.set(state.volume)
        self._updating_audio = False
        self._lbl_audio.configure(text=f"{state.volume:.0f}%")
        icon = "🔇" if state.muted else "🔊"
        fg = BG_CARD_HOVER if state.available else BG_DARK
        txt = TEXT_PRIMARY if state.available else TEXT_MUTED
        self._btn_audio_mute.configure(text=icon, fg_color=fg, text_color=txt)
        self._audio_slider.configure(
            state="normal" if state.available else "disabled",
            progress_color=ACCENT_SECONDARY if state.available else BG_CARD_HOVER,
            button_color=ACCENT if state.available else TEXT_MUTED,
        )
        backend = state.backend.replace("-", " ").title() if state.backend else "Audio"
        if state.available:
            session_label = "session" if state.session_count == 1 else "sessions"
            detail = state.display_name if state.display_name and state.display_name != exe else exe
            hint = f"{backend} · {state.session_count} {session_label} · {detail}"
        else:
            reason_map = {
                "no_session": "No live audio session for this app on PC.",
                "backend_unavailable": "Audio backend unavailable on this platform.",
                "backend_error": "Audio backend could not read live sessions.",
                "no_target": "Select an app to edit audio.",
            }
            hint = reason_map.get(state.reason, "Audio session unavailable right now.")
        self._audio_hint.configure(
            text=hint,
            text_color=TEXT_SECONDARY if state.available else TEXT_MUTED,
        )

    def _on_profile_slider_move(self, _key: str) -> None:
        if self._updating_sliders:
            return
        self._refresh_slider_labels()
        self._profile_debouncer.trigger()

    def _on_audio_slide(self, value: float) -> None:
        if self._updating_audio or not self._selected_exe or not self._audio_available:
            return
        self._lbl_audio.configure(text=f"{value:.0f}%")
        self._audio_debouncer.trigger()

    def _flush_audio_save(self) -> None:
        if not self._selected_exe or not self._audio_available:
            return
        self._ctx.update_program_audio(
            self._selected_exe,
            AudioSettings(volume=float(self._audio_var.get())),
        )

    def _on_audio_mute_toggle(self) -> None:
        if not self._selected_exe or not self._audio_available:
            return
        self._audio_muted = not self._audio_muted
        self._ctx.update_program_audio(
            self._selected_exe,
            AudioSettings(muted=self._audio_muted),
        )
        self._apply_audio_state(self._selected_exe)

    def _flush_profile_save(self) -> None:
        if not self._selected_exe:
            return
        current = self._ctx.profiles.get(self._selected_exe)
        profile = ColorProfile(
            vibrance=float(self._slider_vars["vibrance"].get()),
            brightness=float(self._slider_vars["brightness"].get()),
            contrast=float(self._slider_vars["contrast"].get()),
            gamma=float(self._slider_vars["gamma"].get()),
            hue=int(self._slider_vars["hue"].get()),
            audio=current.audio if current else AudioSettings(),
        )
        self._ctx.update_program_colors(self._selected_exe, profile)

    def _sync_desktop_sliders(self) -> None:
        s = self._ctx.profiles.settings
        self._slider_desktop_v.set(s.desktop_vibrance)
        self._lbl_desktop_v.configure(text=f"{s.desktop_vibrance:.0f}%")

    def _on_desktop_vibrance_slide(self, value: float) -> None:
        self._lbl_desktop_v.configure(text=f"{value:.0f}%")
        self._pending_desktop_v = value
        self._desktop_debouncer.trigger()

    def _flush_desktop_vibrance(self) -> None:
        v = getattr(self, "_pending_desktop_v", self._slider_desktop_v.get())
        self._ctx.update_desktop_settings(desktop_vibrance=v)

    def _on_observer_toggle(self) -> None:
        self._ctx.set_observer(self._chk_observer.get() == 1)
        self._update_status()

    def _on_autostart_toggle(self) -> None:
        enabled = self._chk_autostart.get() == 1
        self._ctx.set_autostart(enabled)
        self._ctx.update_desktop_settings(autostart=enabled)

    def _on_keep_port_toggle(self) -> None:
        if self._updating_keep_port:
            return
        enabled = self._chk_keep_port.get() == 1
        try:
            self._ctx.set_keep_remote_port_open(enabled)
        except Exception as e:
            self._sync_keep_port_checkbox()
            messagebox.showerror("Remote port", str(e), parent=self)

    def _sync_keep_port_checkbox(self) -> None:
        want = 1 if self._ctx.profiles.settings.keep_remote_port_open else 0
        if self._chk_keep_port.get() == want:
            return
        self._updating_keep_port = True
        if want:
            self._chk_keep_port.select()
        else:
            self._chk_keep_port.deselect()
        self._updating_keep_port = False

    def _sync_from_context(self) -> None:
        """Refresh controls after remote edits or profiles.json changes."""
        if self._ctx.profiles.reload_if_stale():
            self._ctx.engine.reload_profiles()

        known = set(self._program_buttons.keys())
        current = set(self._ctx.profiles.list_executables())
        if known != current:
            self._refresh_program_grid()

        if self._selected_exe and self._selected_exe not in current:
            self._clear_program_selection()
        elif self._selected_exe and self._selected_exe in current:
            profile = self._ctx.profiles.get(self._selected_exe)
            if profile:
                self._updating_sliders = True
                self._slider_vars["vibrance"].set(profile.vibrance)
                self._slider_vars["brightness"].set(profile.brightness)
                self._slider_vars["contrast"].set(profile.contrast)
                self._slider_vars["gamma"].set(profile.gamma)
                self._slider_vars["hue"].set(profile.hue)
                self._updating_sliders = False
                self._refresh_slider_labels()
                self._apply_audio_state(self._selected_exe)

        obs = self._ctx.profiles.settings.observer_enabled
        want = 1 if obs else 0
        if self._chk_observer.get() != want:
            if obs:
                self._chk_observer.select()
            else:
                self._chk_observer.deselect()

        self._update_status()
        self._sync_keep_port_checkbox()

    def _on_add_running(self) -> None:
        existing = set(self._ctx.profiles.list_executables())

        def on_pick(exe: str) -> None:
            self._ctx.add_program(exe)
            self._refresh_program_grid()
            self._select_program(exe)

        ProcessPickerDialog(self, on_pick, existing)

    def _on_add_manual(self) -> None:
        exe = self._ctx.pick_exe_manually()
        if not exe:
            return
        if self._ctx.profiles.get(exe):
            self._select_program(exe)
            return
        self._ctx.add_program(exe)
        self._refresh_program_grid()
        self._select_program(exe)

    def _on_remove(self) -> None:
        if not self._selected_exe:
            return
        if self._ctx.remove_program(self._selected_exe):
            self._clear_program_selection()

    def _update_status(self) -> None:
        eng = self._ctx.engine
        if eng.is_running:
            self._engine_label.configure(text="● Active", text_color=SUCCESS)
        else:
            self._engine_label.configure(text="○ Stopped", text_color=TEXT_MUTED)
        n = len(self._ctx.profiles.list_executables())
        focus = eng.active_executable or "—"
        if self._ctx.remote_is_listening:
            remote = " · remote on"
        elif self._ctx.profiles.settings.keep_remote_port_open:
            detail = self._ctx.remote_last_error
            remote = f" · remote error ({detail})" if detail else " · remote error"
        else:
            remote = ""
        self._status_label.configure(text=f"{focus} · {n} profile(s){remote}")

    def _status_tick(self) -> None:
        if self._visible and not self._quitting:
            self._sync_from_context()
            self.after(1500, self._status_tick)

    def _hide_to_tray(self) -> None:
        self._visible = False
        self.withdraw()
        self._tray.notify("VibranceFlow", "Running in the tray. Double-click the icon to open.")

    def _show_from_tray(self) -> None:
        self._visible = True
        self.deiconify()
        self.lift()
        self.focus_force()
        if not self._quitting:
            self.after(1500, self._status_tick)

    def _on_close_attempt(self) -> None:
        self._quit_app()

    def _on_unmap(self, event) -> None:
        if self._quitting or event.widget != self:
            return
        if self.state() == "iconic":
            self._hide_to_tray()

    def _quit_app(self) -> None:
        self._quitting = True
        self._profile_debouncer.cancel()
        self._audio_debouncer.cancel()
        self._desktop_debouncer.cancel()
        release_all_modal_grabs(self)
        self._tray.stop()
        self._ctx.shutdown()
        self.destroy()
