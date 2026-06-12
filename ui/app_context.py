"""Shared context between UI and engine."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any

from tkinter import filedialog

from core.audio_manager import AudioSnapshot, create_audio_manager
from core.autostart import is_autostart_enabled, set_autostart
from core.display_manager import WindowsDisplayManager
from core.engine import LuminaEngine
from core.models import AppSettings, AudioSettings, AudioState, ColorProfile
from core.profile_manager import ProfileManager
from core.remote.handlers import RemoteCommandHandler
from core.remote.protocol import ProtocolError
from core.remote.firewall import ensure_firewall_rule
from core.remote.health import (
    PortInUseError,
    RemoteStartError,
    is_port_in_use,
    verify_remote_dependencies,
)
from core.remote.server import RemoteServer

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
        self.audio = create_audio_manager()
        self.engine = LuminaEngine(self.display, self.profiles, audio=self.audio)
        self._schedule_main: Callable[[Callable[[], None]], None] | None = None
        self._remote: RemoteServer | None = None
        self._last_firewall_warning: str | None = None
        self._ui_sync_callbacks: list[Callable[[], None]] = []
        self._pairing_close_callbacks: list[Callable[[], None]] = []
        if self.profiles.settings.observer_enabled:
            self.engine.start()

    def attach_ui_scheduler(self, schedule: Callable[[Callable[[], None]], None]) -> None:
        """Called from the GUI with ``root.after`` for thread-safe UI/remote work."""
        self._schedule_main = schedule
        if self.profiles.settings.keep_remote_port_open:
            try:
                self.ensure_remote_server()
            except Exception as e:
                logger.warning("Could not auto-start remote server: %s", e, exc_info=True)

    def on_ui_sync(self, callback: Callable[[], None]) -> None:
        self._ui_sync_callbacks.append(callback)

    def on_pairing_complete(self, callback: Callable[[], None]) -> None:
        """Called when a phone pairs (PIN or first encrypted frame)."""
        self._pairing_close_callbacks.append(callback)

    def clear_pairing_complete_callbacks(self) -> None:
        self._pairing_close_callbacks.clear()

    def _notify_ui_sync(self) -> None:
        if self._schedule_main is None:
            return

        def _run() -> None:
            for cb in list(self._ui_sync_callbacks):
                try:
                    cb()
                except Exception:
                    logger.debug("UI sync callback failed", exc_info=True)

        self._schedule_main(_run)

    def _notify_pairing_complete(self) -> None:
        if not self._pairing_close_callbacks or self._schedule_main is None:
            return

        def _run() -> None:
            for cb in list(self._pairing_close_callbacks):
                try:
                    cb()
                except Exception:
                    logger.debug("Pairing close callback failed", exc_info=True)
            self._pairing_close_callbacks.clear()

        self._schedule_main(_run)

    def shutdown(self) -> None:
        self.stop_remote_server()
        if self.engine.is_running:
            self.engine.stop()
        self.audio.shutdown()
        self.display.shutdown()

    @property
    def remote_is_running(self) -> bool:
        return self._remote is not None and self._remote.is_running

    @property
    def remote_is_listening(self) -> bool:
        return self._remote is not None and self._remote.is_listening

    @property
    def remote_last_error(self) -> str | None:
        if self._remote is None:
            return None
        return self._remote.last_start_error

    @property
    def remote_client_count(self) -> int:
        if self._remote is None:
            return 0
        return self._remote.client_count

    @property
    def pairing_payload(self) -> dict[str, Any]:
        if self._remote is None:
            return {}
        return self._remote.pairing_payload

    def _ensure_remote_instance(self) -> RemoteServer:
        if self._remote is None:
            handler = RemoteCommandHandler(
                get_state=self._remote_get_state,
                set_sliders=self._remote_set_sliders,
                set_audio=self._remote_set_audio,
                set_observer=self.set_observer,
                reset_profile=self._remote_reset_profile,
            )
            self._remote = RemoteServer(
                handler,
                on_main_thread=self._schedule_main,
                on_paired=self._notify_pairing_complete,
            )
        return self._remote

    def _start_remote_listening(self) -> str | None:
        remote = self._ensure_remote_instance()
        if remote.is_listening:
            return None
        if is_port_in_use(remote.port):
            raise PortInUseError(
                f"Port {remote.port} is already in use. "
                "Close the other VibranceFlow or any app using this port."
            )
        warn = ensure_firewall_rule(remote.port)
        remote.restart()
        if not remote.wait_until_ready(5.0):
            err = remote.last_start_error or "Remote server did not start listening."
            raise RemoteStartError(err)
        return warn

    def ensure_remote_server(self) -> RemoteServer:
        if self._schedule_main is None:
            raise RuntimeError("UI scheduler not attached")
        dep_err = verify_remote_dependencies()
        if dep_err:
            raise RemoteStartError(dep_err)
        warn = self._start_remote_listening()
        if warn:
            self._last_firewall_warning = warn
        remote = self._remote
        if remote is None:
            raise RemoteStartError("Remote server was not initialized.")
        return remote

    def prepare_pairing_session(self, *, persist_keep_port: bool = True) -> RemoteServer:
        """Start or restart the LAN server for Pair Mobile (works with keep-port unchecked)."""
        if self._schedule_main is None:
            raise RuntimeError("UI scheduler not attached")
        dep_err = verify_remote_dependencies()
        if dep_err:
            raise RemoteStartError(dep_err)
        warn = self._start_remote_listening()
        assert self._remote is not None
        self._remote.refresh_pairing_pin()
        if warn:
            self._last_firewall_warning = warn
        if persist_keep_port and not self.profiles.settings.keep_remote_port_open:
            self._persist_keep_port_setting(True)
        self._notify_ui_sync()
        return self._remote

    def consume_firewall_warning(self) -> str | None:
        warn = self._last_firewall_warning
        self._last_firewall_warning = None
        return warn

    def regenerate_pairing_key(self) -> None:
        server = self.ensure_remote_server()
        server.regenerate_key()

    def refresh_pairing_pin(self) -> str:
        server = self.ensure_remote_server()
        return server.refresh_pairing_pin()

    @property
    def pairing_pin(self) -> str:
        if self._remote is None:
            return ""
        return self._remote.pairing_pin

    def stop_remote_server(self) -> None:
        if self._remote is not None:
            self._remote.stop()

    def disconnect_remote_clients(self, *, rotate_key: bool = False) -> None:
        if self._remote is None:
            return
        self._remote.disconnect_all_clients()
        if rotate_key:
            self._remote.regenerate_key()

    def activate_keep_remote_port(self) -> None:
        """Enable persistent port after firewall allows LAN (Pair Mobile)."""
        if not self.profiles.settings.keep_remote_port_open:
            self.set_keep_remote_port_open(True)
        else:
            self.ensure_remote_server()
            self._notify_ui_sync()

    def reset_program_to_gpu_default(self, exe_name: str) -> None:
        current = self.profiles.get(exe_name)
        audio = current.audio if current else AudioSettings()
        profile = ColorProfile(
            vibrance=self.display.gpu_default_profile.vibrance,
            brightness=self.display.gpu_default_profile.brightness,
            contrast=self.display.gpu_default_profile.contrast,
            gamma=self.display.gpu_default_profile.gamma,
            hue=self.display.gpu_default_profile.hue,
            audio=audio,
        )
        self.profiles.upsert(exe_name, profile)
        self.engine.reload_profiles()
        active = self.engine.active_executable
        if active and active.lower() == exe_name.lower():
            self.display.apply_profile(profile)
            self.audio.apply_settings(exe_name, profile.audio)

    def _resolve_target_exe(self, exe: str | None) -> str | None:
        if exe:
            return exe
        return self.engine.active_executable

    def _remote_get_state(self) -> dict[str, Any]:
        if self.profiles.reload_if_stale():
            self.engine.reload_profiles()
        return self._build_remote_state()

    def _build_remote_state(self) -> dict[str, Any]:
        audio_snapshot = self.audio.snapshot()
        programs: list[dict[str, Any]] = []
        for exe in self.profiles.list_executables():
            profile = self.profiles.get(exe)
            if profile:
                programs.append(
                    {
                        "exe": exe,
                        "sliders": profile.to_dict(),
                        "audio": self._program_audio_state(exe, profile, audio_snapshot).to_dict(),
                    }
                )
        return {
            "observer_enabled": self.profiles.settings.observer_enabled,
            "active_exe": self.engine.active_executable,
            "sliders": self._current_sliders_dict(),
            "audio": self._current_audio_dict(audio_snapshot),
            "programs": programs,
        }

    def _current_sliders_dict(self) -> dict[str, float | int]:
        active = self.engine.active_executable
        if active:
            profile = self.profiles.get(active)
            if profile:
                return profile.to_dict()
        desktop = self.profiles.desktop_profile()
        return desktop.to_dict()

    def _current_audio_dict(self, snapshot: AudioSnapshot | None = None) -> dict[str, Any]:
        active = self.engine.active_executable
        profile = self.profiles.get(active) if active else None
        return self._program_audio_state(active, profile, snapshot).to_dict()

    def _program_audio_state(
        self,
        exe_name: str | None,
        profile: ColorProfile | None = None,
        snapshot: AudioSnapshot | None = None,
    ) -> AudioState:
        saved = profile.audio if profile is not None else AudioSettings()
        return self.audio.describe(exe_name, saved, snapshot)

    def get_program_audio_state(self, exe_name: str | None) -> AudioState:
        profile = self.profiles.get(exe_name) if exe_name else None
        return self._program_audio_state(exe_name, profile)

    def _remote_set_sliders(self, profile: ColorProfile, exe: str | None) -> None:
        target = self._resolve_target_exe(exe)
        if target:
            self.update_program_colors(target, profile)
        else:
            self.display.apply_profile(profile)
        self._notify_ui_sync()

    def _remote_set_audio(self, settings: AudioSettings, exe: str | None) -> None:
        target = self._resolve_target_exe(exe)
        if not target:
            raise ProtocolError("no target executable for audio")
        self.update_program_audio(target, settings)
        self._notify_ui_sync()

    def _remote_reset_profile(self, exe: str | None) -> None:
        target = self._resolve_target_exe(exe)
        if not target:
            raise ProtocolError("no target executable for reset")
        self.reset_program_to_gpu_default(target)
        self._notify_ui_sync()

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
                keep_remote_port_open=settings.keep_remote_port_open,
            )
        )
        if enabled:
            self.engine.reload_profiles()
            if not self.engine.is_running:
                self.engine.start()
        elif self.engine.is_running:
            self.engine.stop()
        self._notify_ui_sync()

    def _persist_keep_port_setting(self, enabled: bool) -> None:
        settings = self.profiles.settings
        self.profiles.update_settings(
            AppSettings(
                desktop_vibrance=settings.desktop_vibrance,
                desktop_brightness=settings.desktop_brightness,
                desktop_contrast=settings.desktop_contrast,
                desktop_gamma=settings.desktop_gamma,
                desktop_hue=settings.desktop_hue,
                observer_enabled=settings.observer_enabled,
                affect_primary_only=settings.affect_primary_only,
                autostart=settings.autostart,
                keep_remote_port_open=enabled,
            )
        )

    def set_keep_remote_port_open(self, enabled: bool) -> None:
        settings = self.profiles.settings
        self._persist_keep_port_setting(enabled)
        try:
            if enabled:
                self.ensure_remote_server()
            else:
                self.stop_remote_server()
        except Exception:
            if enabled:
                self.profiles.update_settings(
                    AppSettings(
                        desktop_vibrance=settings.desktop_vibrance,
                        desktop_brightness=settings.desktop_brightness,
                        desktop_contrast=settings.desktop_contrast,
                        desktop_gamma=settings.desktop_gamma,
                        desktop_hue=settings.desktop_hue,
                        observer_enabled=settings.observer_enabled,
                        affect_primary_only=settings.affect_primary_only,
                        autostart=settings.autostart,
                        keep_remote_port_open=False,
                    )
                )
            raise
        self._notify_ui_sync()

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
            keep_remote_port_open=kwargs.get(
                "keep_remote_port_open", s.keep_remote_port_open
            ),
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
        self._notify_ui_sync()

    def remove_program(self, exe_name: str) -> bool:
        ok = self.profiles.remove(exe_name)
        if ok:
            self.engine.reload_profiles()
            self._notify_ui_sync()
        return ok

    def update_program(self, exe_name: str, profile: ColorProfile) -> None:
        self.profiles.upsert(exe_name, profile)
        active = self.engine.active_executable
        if active and active.lower() == exe_name.lower():
            self.display.apply_profile(profile)
            self.audio.apply_settings(exe_name, profile.audio)
        self._notify_ui_sync()

    def update_program_colors(self, exe_name: str, profile: ColorProfile) -> None:
        existing = self.profiles.get(exe_name)
        merged = ColorProfile(
            vibrance=profile.vibrance,
            brightness=profile.brightness,
            contrast=profile.contrast,
            gamma=profile.gamma,
            hue=profile.hue,
            audio=existing.audio if existing else AudioSettings(),
        )
        self.update_program(exe_name, merged)

    def update_program_audio(self, exe_name: str, settings: AudioSettings) -> None:
        existing = self.profiles.get(exe_name) or DEFAULT_GAME_PROFILE
        merged_audio = AudioSettings(
            volume=settings.volume if settings.volume is not None else existing.audio.volume,
            muted=settings.muted if settings.muted is not None else existing.audio.muted,
        )
        merged = ColorProfile(
            vibrance=existing.vibrance,
            brightness=existing.brightness,
            contrast=existing.contrast,
            gamma=existing.gamma,
            hue=existing.hue,
            audio=merged_audio,
        )
        self.profiles.upsert(exe_name, merged)
        self.audio.apply_settings(exe_name, merged.audio)
        self._notify_ui_sync()

    def pick_exe_manually(self) -> str | None:
        path = filedialog.askopenfilename(
            title="Select executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
        )
        if not path:
            return None
        return os.path.basename(path)
