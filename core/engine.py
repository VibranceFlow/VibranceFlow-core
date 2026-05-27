"""Main engine — foreground polling loop and state machine."""

from __future__ import annotations

import logging
import threading
from typing import Literal

from core.audio_manager import AudioManager
from core.display_manager import WindowsDisplayManager
from core.profile_manager import ProfileManager
from core.window_monitor import get_foreground_executable

logger = logging.getLogger(__name__)

EngineState = Literal["desktop", "profile"]


class LuminaEngine:
    def __init__(
        self,
        display: WindowsDisplayManager,
        profiles: ProfileManager,
        audio: AudioManager | None = None,
        poll_interval: float = 1.0,
    ) -> None:
        self._display = display
        self._profiles = profiles
        self._audio = audio
        self._poll_interval = poll_interval
        self._active_exe: str | None = None
        self._state: EngineState = "desktop"
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def state(self) -> EngineState:
        return self._state

    @property
    def active_executable(self) -> str | None:
        return self._active_exe

    def reload_profiles(self) -> None:
        self._profiles.reload()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="LuminaEngine", daemon=True)
        self._thread.start()
        logger.info("Engine started (interval=%.1fs).", self._poll_interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._poll_interval + 2.0)
            self._thread = None
        try:
            self._display.restore_defaults()
        except Exception as e:
            logger.error("Failed to restore baseline on stop: %s", e)
        self._active_exe = None
        self._state = "desktop"
        logger.info("Engine stopped.")

    def _run(self) -> None:
        while not self._stop_event.wait(self._poll_interval):
            try:
                self._tick()
            except Exception:
                logger.exception("Engine tick error.")

    def _tick(self) -> None:
        exe = get_foreground_executable()
        if exe == self._active_exe:
            self._sync_active_audio(exe)
            return

        prev = self._active_exe
        self._active_exe = exe

        profile = self._profiles.get(exe) if exe else None
        if profile is not None:
            self._display.apply_profile(profile)
            self._sync_active_audio(exe, profile)
            self._state = "profile"
            logger.info("Profile applied: %s (was: %s)", exe, prev)
        else:
            self._apply_desktop()
            self._state = "desktop"
            logger.info("Desktop restored (foreground: %s, was: %s)", exe, prev)

    def _apply_desktop(self) -> None:
        if not self._profiles.settings.observer_enabled:
            self._display.restore_defaults()
            return
        self._display.apply_profile(self._profiles.desktop_profile())

    def _sync_active_audio(self, exe: str | None, profile=None) -> None:
        if self._audio is None or not exe:
            return
        current = profile or self._profiles.get(exe)
        if current is None or not current.audio.configured:
            return
        self._audio.apply_settings(exe, current.audio)
