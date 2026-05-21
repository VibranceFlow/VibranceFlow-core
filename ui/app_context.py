"""Shared context between UI and engine."""

from __future__ import annotations

import logging
import os
from tkinter import filedialog

from core.autostart import is_autostart_enabled, set_autostart
from core.display_manager import WindowsDisplayManager
from core.engine import LuminaEngine
from core.models import AppSettings, ColorProfile
from core.profile_manager import ProfileManager

logger = logging.getLogger(__name__)

DEFAULT_GAME_PROFILE = ColorProfile(
    vibrance=75.0,
    brightness=42.0,
    contrast=50.0,
    gamma=1.1,
    hue=0,
)


class LuminaAppContext:
    def __init__(self) -> None:
        self.profiles = ProfileManager()
        self.display = WindowsDisplayManager()
        self.engine = LuminaEngine(self.display, self.profiles)
        if self.profiles.settings.observer_enabled:
            self.engine.start()

    def shutdown(self) -> None:
        if self.engine.is_running:
            self.engine.stop()
        self.display.shutdown()

    def set_observer(self, enabled: bool) -> None:
        settings = self.profiles.settings
        self.profiles.update_settings(
            AppSettings(
                desktop_vibrance=settings.desktop_vibrance,
                desktop_brightness=settings.desktop_brightness,
                desktop_contrast=settings.desktop_contrast,
                desktop_gamma=settings.desktop_gamma,
                desktop_hue=settings.desktop_hue,
                observer_enabled=enabled,
                affect_primary_only=settings.affect_primary_only,
                autostart=settings.autostart,
            )
        )
        if enabled:
            self.engine.reload_profiles()
            if not self.engine.is_running:
                self.engine.start()
        elif self.engine.is_running:
            self.engine.stop()

    def _merge_settings(self, **kwargs) -> AppSettings:
        s = self.profiles.settings
        return AppSettings(
            desktop_vibrance=kwargs.get("desktop_vibrance", s.desktop_vibrance),
            desktop_brightness=kwargs.get("desktop_brightness", s.desktop_brightness),
            desktop_contrast=kwargs.get("desktop_contrast", s.desktop_contrast),
            desktop_gamma=kwargs.get("desktop_gamma", s.desktop_gamma),
            desktop_hue=kwargs.get("desktop_hue", s.desktop_hue),
            observer_enabled=kwargs.get("observer_enabled", s.observer_enabled),
            affect_primary_only=kwargs.get("affect_primary_only", s.affect_primary_only),
            autostart=kwargs.get("autostart", s.autostart),
        )

    def update_desktop_settings(self, **kwargs) -> None:
        updated = self._merge_settings(**kwargs)
        self.profiles.update_settings(updated)
        self.engine.reload_profiles()
        if self.engine.state == "desktop" and self.engine.is_running:
            self.display.apply_profile(self.profiles.desktop_profile())

    def set_autostart(self, enabled: bool) -> None:
        set_autostart(enabled)
        self.update_desktop_settings(autostart=enabled)

    def sync_autostart_checkbox(self) -> bool:
        return is_autostart_enabled()

    def add_program(self, exe_name: str, profile: ColorProfile | None = None) -> None:
        self.profiles.upsert(exe_name, profile or DEFAULT_GAME_PROFILE)
        self.engine.reload_profiles()

    def remove_program(self, exe_name: str) -> bool:
        ok = self.profiles.remove(exe_name)
        if ok:
            self.engine.reload_profiles()
        return ok

    def update_program(self, exe_name: str, profile: ColorProfile) -> None:
        self.profiles.upsert(exe_name, profile)
        active = self.engine.active_executable
        if active and active.lower() == exe_name.lower():
            self.display.apply_profile(profile)

    def pick_exe_manually(self) -> str | None:
        path = filedialog.askopenfilename(
            title="Select executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
        )
        if not path:
            return None
        return os.path.basename(path)
