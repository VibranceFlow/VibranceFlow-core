"""LuminaSync main window — compact layout."""

from __future__ import annotations

import customtkinter as ctk

from core.models import ColorProfile
from ui.app_context import LuminaAppContext
from ui.process_picker import ProcessPickerDialog
from ui.theme import (
    ACCENT,
    ACCENT_SECONDARY,
    BG_CARD,
    BG_CARD_HOVER,
    BG_DARK,
    BG_INPUT,
    DANGER,
    FONT_BODY,
    FONT_SMALL,
    FONT_TITLE,
    SUCCESS,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from ui.tray import TrayController
from ui.util import Debouncer

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class LuminaSyncWindow(ctk.CTk):
    def __init__(self, ctx: LuminaAppContext, *, start_hidden: bool = False) -> None:
        super().__init__()
        self._ctx = ctx
        self._selected_exe: str | None = None
        self._program_buttons: dict[str, ctk.CTkButton] = {}
        self._slider_vars: dict[str, ctk.DoubleVar | ctk.IntVar] = {}
        self._updating_sliders = False
        self._quitting = False
        self._visible = not start_hidden

        self.title("LuminaSync")
        self._size_compact = (520, 380)
        self._size_expanded = (520, 560)
        self._expanded = False
        self.geometry(f"{self._size_compact[0]}x{self._size_compact[1]}")
        self.minsize(480, 360)
        self.configure(fg_color=BG_DARK)

        self._build_header()
        self._build_settings()
        self._build_programs()
        self._build_profile_editor()
        self._build_status()

        self._profile_debouncer = Debouncer(self, 180, self._flush_profile_save)
        self._desktop_debouncer = Debouncer(self, 180, self._flush_desktop_vibrance)

        self._tray = TrayController(on_show=self._show_from_tray, on_quit=self._quit_app)
        self._tray.start()

        self._refresh_program_grid()
        self._sync_desktop_sliders()
        self._hide_profile_panel()
        self._update_status()

        self.protocol("WM_DELETE_WINDOW", self._on_close_attempt)
        self.bind("<Unmap>", self._on_unmap)

        if start_hidden:
            self.withdraw()
        else:
            self.after(2000, self._status_tick)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=44)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="LuminaSync",
            font=("Segoe UI", 16, "bold"),
            text_color=ACCENT,
        ).pack(side="left", padx=12, pady=8)
        ctk.CTkLabel(
            header,
            text="◆",
            font=("Segoe UI", 14),
            text_color=ACCENT_SECONDARY,
        ).pack(side="right", padx=12)

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

        self._programs_scroll = ctk.CTkScrollableFrame(
            box,
            fg_color=BG_DARK,
            height=72,
            orientation="horizontal",
        )
        self._programs_scroll.pack(fill="x", padx=6, pady=(0, 6))

    def _build_profile_editor(self) -> None:
        self._profile_box = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        self._profile_inner = ctk.CTkFrame(self._profile_box, fg_color="transparent")
        self._sliders_container = ctk.CTkFrame(self._profile_inner, fg_color="transparent")

        title_row = ctk.CTkFrame(self._profile_inner, fg_color="transparent")
        title_row.pack(fill="x", padx=8, pady=(6, 2))
        self._profile_title = ctk.CTkLabel(
            title_row,
            text="",
            font=FONT_SMALL,
            text_color=ACCENT,
        )
        self._profile_title.pack(side="left")

        specs = [
            ("vibrance", "Vib", 0, 100, 100),
            ("brightness", "Bri", -50, 50, 100),
            ("contrast", "Con", -50, 50, 100),
            ("gamma", "Gam", 0.4, 2.8, 24),
            ("hue", "Mat", 0, 359, 359),
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

    def _build_status(self) -> None:
        self._status_bar = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=28)
        self._status_bar.pack(fill="x", side="bottom")
        self._status_bar.pack_propagate(False)
        bar = self._status_bar
        self._status_label = ctk.CTkLabel(
            bar,
            text="",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        )
        self._status_label.pack(side="left", padx=10)
        self._engine_label = ctk.CTkLabel(bar, text="", font=FONT_SMALL)
        self._engine_label.pack(side="right", padx=10)

    def _hide_profile_panel(self) -> None:
        self._profile_box.pack_forget()
        self._set_window_expanded(False)

    def _show_profile_panel(self, exe: str) -> None:
        self._profile_box.pack(fill="x", padx=10, pady=(4, 6), before=self._status_bar)
        self._profile_inner.pack(fill="x", padx=4, pady=4)
        self._sliders_container.pack(fill="x", padx=4, pady=(0, 8))
        self._profile_title.configure(text=exe)
        self._set_window_expanded(True)

    def _set_window_expanded(self, expanded: bool) -> None:
        if expanded == self._expanded:
            return
        self._expanded = expanded
        w, h = self._size_expanded if expanded else self._size_compact
        self.minsize(480, 500 if expanded else 360)
        self.geometry(f"{w}x{h}")
        self.update_idletasks()

    def _refresh_program_grid(self) -> None:
        for w in self._programs_scroll.winfo_children():
            w.destroy()
        self._program_buttons.clear()

        exes = self._ctx.profiles.list_executables()
        if not exes:
            ctk.CTkLabel(
                self._programs_scroll,
                text="(empty)",
                font=FONT_SMALL,
                text_color=TEXT_MUTED,
            ).pack(padx=8, pady=4)
            return

        for exe in exes:
            short = exe.replace(".exe", "")[:10]
            sel = exe == self._selected_exe
            btn = ctk.CTkButton(
                self._programs_scroll,
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
            btn.pack(side="left", padx=3, pady=4)
            self._program_buttons[exe] = btn

    def _select_program(self, exe: str) -> None:
        self._selected_exe = exe
        for name, btn in self._program_buttons.items():
            sel = name == exe
            btn.configure(fg_color=ACCENT if sel else BG_CARD_HOVER, text_color=BG_DARK if sel else TEXT_PRIMARY)
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

    def _clear_program_selection(self) -> None:
        self._selected_exe = None
        self._hide_profile_panel()
        self._refresh_program_grid()

    def _refresh_slider_labels(self) -> None:
        if not self._selected_exe:
            return
        self._lbl_vibrance.configure(text=f"{self._slider_vars['vibrance'].get():.0f}%")
        self._lbl_brightness.configure(text=f"{self._slider_vars['brightness'].get():+.0f}%")
        self._lbl_contrast.configure(text=f"{self._slider_vars['contrast'].get():+.0f}%")
        self._lbl_gamma.configure(text=f"{self._slider_vars['gamma'].get():.2f}")
        self._lbl_hue.configure(text=f"{int(self._slider_vars['hue'].get())}°")

    def _on_profile_slider_move(self, _key: str) -> None:
        if self._updating_sliders:
            return
        self._refresh_slider_labels()
        self._profile_debouncer.trigger()

    def _flush_profile_save(self) -> None:
        if not self._selected_exe:
            return
        profile = ColorProfile(
            vibrance=float(self._slider_vars["vibrance"].get()),
            brightness=float(self._slider_vars["brightness"].get()),
            contrast=float(self._slider_vars["contrast"].get()),
            gamma=float(self._slider_vars["gamma"].get()),
            hue=int(self._slider_vars["hue"].get()),
        )
        self._ctx.update_program(self._selected_exe, profile)

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
        self._status_label.configure(text=f"{focus} · {n} profile(s)")

    def _status_tick(self) -> None:
        if self._visible and not self._quitting:
            self._update_status()
            self.after(2000, self._status_tick)

    def _hide_to_tray(self) -> None:
        self._visible = False
        self.withdraw()
        self._tray.notify("LuminaSync", "Running in the tray. Double-click the icon to open.")

    def _show_from_tray(self) -> None:
        self._visible = True
        self.deiconify()
        self.lift()
        self.focus_force()
        if not self._quitting:
            self.after(2000, self._status_tick)

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
        self._desktop_debouncer.cancel()
        self._tray.stop()
        self._ctx.shutdown()
        self.destroy()
