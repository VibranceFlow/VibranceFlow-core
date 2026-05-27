"""Per-application audio control backends."""

from __future__ import annotations

import ctypes
import logging
import os
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from ctypes import byref, create_unicode_buffer, wintypes

from core.models import AudioSettings, AudioState

logger = logging.getLogger(__name__)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_PATH_BUF_CHARS = 32768
_WINDOWS_SESSION_STATES = {
    0: "inactive",
    1: "active",
    2: "expired",
}

if sys.platform == "win32":
    try:
        from pycaw.callbacks import AudioSessionEvents as _PycawAudioSessionEvents
        from pycaw.callbacks import AudioSessionNotification as _PycawAudioSessionNotification
    except Exception:  # pragma: no cover - optional runtime import
        class _PycawAudioSessionEvents:  # type: ignore[no-redef]
            pass

        class _PycawAudioSessionNotification:  # type: ignore[no-redef]
            pass
else:
    class _PycawAudioSessionEvents:
        pass

    class _PycawAudioSessionNotification:
        pass


@dataclass(frozen=True)
class AudioSessionRef:
    """Runtime reference to a live audio session or stream."""

    backend: str
    session_id: str
    instance_id: str
    process_id: int
    exe_name: str
    display_name: str
    state: str
    volume: float
    muted: bool

    @property
    def key(self) -> tuple[str, str, int]:
        return (self.session_id, self.instance_id, self.process_id)


@dataclass(frozen=True)
class AudioSnapshot:
    """Point-in-time view of live sessions known by a backend."""

    backend: str
    sessions: tuple[AudioSessionRef, ...] = ()
    reason: str = "no_session"

    def resolve(self, exe_name: str | None) -> tuple[AudioSessionRef, ...]:
        if not exe_name:
            return ()
        key = _normalize_exe(exe_name)
        return tuple(
            session
            for session in self.sessions
            if _normalize_exe(session.exe_name) == key and session.state != "expired"
        )

    def describe(self, exe_name: str | None, saved: AudioSettings | None = None) -> AudioState:
        saved = saved or AudioSettings()
        matched = self.resolve(exe_name)
        if not matched:
            return AudioState(
                available=False,
                volume=saved.volume if saved.volume is not None else 100.0,
                muted=saved.muted if saved.muted is not None else False,
                session_count=0,
                backend=self.backend,
                display_name=exe_name or "",
                reason="no_target" if not exe_name else self.reason,
            )

        volumes = [session.volume for session in matched]
        mute_values = {session.muted for session in matched}
        mixed = len({round(v, 2) for v in volumes}) > 1 or len(mute_values) > 1
        return AudioState(
            available=True,
            volume=max(0.0, min(100.0, sum(volumes) / len(volumes))),
            muted=all(session.muted for session in matched),
            session_count=len(matched),
            backend=self.backend,
            display_name=_pick_display_name(matched, exe_name or ""),
            reason="mixed" if mixed else "ok",
        )


class AudioManager:
    """Cross-platform audio manager interface."""

    backend_name = "none"

    def snapshot(self) -> AudioSnapshot:
        return AudioSnapshot(backend=self.backend_name, reason="backend_unavailable")

    def describe(
        self,
        exe_name: str | None,
        saved: AudioSettings | None = None,
        snapshot: AudioSnapshot | None = None,
    ) -> AudioState:
        return (snapshot or self.snapshot()).describe(exe_name, saved)

    def apply_settings(
        self,
        exe_name: str,
        saved: AudioSettings,
        snapshot: AudioSnapshot | None = None,
    ) -> bool:
        return False

    def shutdown(self) -> None:
        return None


class WindowsAudioManager(AudioManager):
    """WASAPI session-volume control for Windows shared-mode apps."""

    backend_name = "windows-wasapi"

    def __init__(self) -> None:
        self._enabled = False
        self._lock = threading.Lock()
        self._dirty = True
        self._last_refresh_at = 0.0
        self._snapshot_ttl_s = 1.0
        self._snapshot_cache = AudioSnapshot(backend=self.backend_name, reason="backend_unavailable")
        self._comtypes = None
        self._audio_utilities = None
        self._simple_audio_volume = None
        self._session_manager = None
        self._session_notification = None
        self._session_callbacks: dict[tuple[str, str, int], tuple[object, object]] = {}
        if sys.platform != "win32":
            return
        try:
            import comtypes
            from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume

            self._comtypes = comtypes
            self._audio_utilities = AudioUtilities
            self._simple_audio_volume = ISimpleAudioVolume
            self._enabled = True
            self._snapshot_cache = AudioSnapshot(backend=self.backend_name, reason="no_session")
        except Exception as exc:
            logger.warning("Per-app audio control unavailable: %s", exc)

    @contextmanager
    def _com_scope(self):
        if not self._enabled or self._comtypes is None:
            yield
            return
        self._comtypes.CoInitialize()
        try:
            yield
        finally:
            self._comtypes.CoUninitialize()

    def invalidate(self) -> None:
        with self._lock:
            self._dirty = True

    def snapshot(self) -> AudioSnapshot:
        if not self._enabled:
            return AudioSnapshot(backend=self.backend_name, reason="backend_unavailable")
        with self._lock:
            now = time.monotonic()
            if not self._dirty and (now - self._last_refresh_at) < self._snapshot_ttl_s:
                return self._snapshot_cache
            with self._com_scope():
                self._snapshot_cache = self._refresh_snapshot_locked()
            self._dirty = False
            self._last_refresh_at = now
            return self._snapshot_cache

    def apply_settings(
        self,
        exe_name: str,
        saved: AudioSettings,
        snapshot: AudioSnapshot | None = None,
    ) -> bool:
        if not self._enabled or not exe_name or not saved.configured or self._audio_utilities is None:
            return False
        target_keys = {session.key for session in (snapshot or self.snapshot()).resolve(exe_name)}
        if not target_keys:
            return False

        matched = False
        with self._com_scope():
            try:
                sessions = self._audio_utilities.GetAllSessions()
            except Exception as exc:
                logger.debug("Audio session query failed: %s", exc)
                return False
            for session in sessions:
                ref = _windows_session_ref(session, self.backend_name, self._simple_audio_volume)
                if ref is None or ref.key not in target_keys:
                    continue
                simple = _simple_volume_interface(session, self._simple_audio_volume)
                if simple is None:
                    continue
                try:
                    if saved.volume is not None:
                        simple.SetMasterVolume(max(0.0, min(1.0, saved.volume / 100.0)), None)
                    if saved.muted is not None:
                        simple.SetMute(bool(saved.muted), None)
                    matched = True
                except Exception:
                    logger.debug("Failed to apply audio settings to %s", exe_name, exc_info=True)
        if matched:
            self.invalidate()
        return matched

    def shutdown(self) -> None:
        if not self._enabled:
            return
        with self._lock:
            callbacks = list(self._session_callbacks.values())
            self._session_callbacks.clear()
            manager = self._session_manager
            notification = self._session_notification
            self._session_manager = None
            self._session_notification = None
            self._dirty = True
        with self._com_scope():
            for session, callback in callbacks:
                try:
                    session.unregister_notification()
                except Exception:
                    logger.debug("Could not unregister session callback", exc_info=True)
            if manager is not None and notification is not None:
                try:
                    manager.UnregisterSessionNotification(notification)
                except Exception:
                    logger.debug("Could not unregister session manager callback", exc_info=True)

    def _refresh_snapshot_locked(self) -> AudioSnapshot:
        assert self._audio_utilities is not None
        self._ensure_manager_callback_locked()
        try:
            sessions = self._audio_utilities.GetAllSessions()
        except Exception as exc:
            logger.debug("Audio session snapshot failed: %s", exc)
            return AudioSnapshot(backend=self.backend_name, reason="backend_error")

        refs: list[AudioSessionRef] = []
        active_keys: set[tuple[str, str, int]] = set()
        for session in sessions:
            ref = _windows_session_ref(session, self.backend_name, self._simple_audio_volume)
            if ref is None:
                continue
            refs.append(ref)
            active_keys.add(ref.key)
            self._ensure_session_callback_locked(ref.key, session)

        stale_keys = set(self._session_callbacks) - active_keys
        for key in stale_keys:
            session, callback = self._session_callbacks.pop(key)
            try:
                session.unregister_notification()
            except Exception:
                logger.debug("Could not unregister stale session callback", exc_info=True)

        refs.sort(key=lambda ref: (ref.exe_name.lower(), ref.display_name.lower(), ref.process_id))
        return AudioSnapshot(
            backend=self.backend_name,
            sessions=tuple(refs),
            reason="no_session" if not refs else "ok",
        )

    def _ensure_manager_callback_locked(self) -> None:
        if self._session_manager is not None or self._audio_utilities is None:
            return
        try:
            manager = self._audio_utilities.GetAudioSessionManager()
            notification = _WindowsSessionNotification(self)
            manager.RegisterSessionNotification(notification)
            self._session_manager = manager
            self._session_notification = notification
        except Exception:
            logger.debug("Could not register session manager callback", exc_info=True)

    def _ensure_session_callback_locked(self, key: tuple[str, str, int], session) -> None:
        if key in self._session_callbacks:
            return
        try:
            callback = _WindowsSessionEvents(self)
            session.register_notification(callback)
            self._session_callbacks[key] = (session, callback)
        except Exception:
            logger.debug("Could not register session callback for %s", key, exc_info=True)


class LinuxPulseAudioManager(AudioManager):
    """PulseAudio / pipewire-pulse sink-input volume control."""

    backend_name = "linux-pulseaudio"

    def __init__(self) -> None:
        self._enabled = False
        self._pulsectl = None
        if not sys.platform.startswith("linux"):
            return
        try:
            import pulsectl

            self._pulsectl = pulsectl
            self._enabled = True
        except Exception as exc:
            logger.warning("Linux per-app audio control unavailable: %s", exc)

    def snapshot(self) -> AudioSnapshot:
        if not self._enabled or self._pulsectl is None:
            return AudioSnapshot(backend=self.backend_name, reason="backend_unavailable")
        refs: list[AudioSessionRef] = []
        try:
            with self._pulsectl.Pulse("vibranceflow-core") as pulse:
                for sink_input in pulse.sink_input_list():
                    ref = _pulse_session_ref(sink_input, self.backend_name)
                    if ref is not None:
                        refs.append(ref)
        except Exception as exc:
            logger.debug("PulseAudio snapshot failed: %s", exc)
            return AudioSnapshot(backend=self.backend_name, reason="backend_error")
        refs.sort(key=lambda ref: (ref.exe_name.lower(), ref.display_name.lower(), ref.process_id))
        return AudioSnapshot(
            backend=self.backend_name,
            sessions=tuple(refs),
            reason="no_session" if not refs else "ok",
        )

    def apply_settings(
        self,
        exe_name: str,
        saved: AudioSettings,
        snapshot: AudioSnapshot | None = None,
    ) -> bool:
        if not self._enabled or self._pulsectl is None or not exe_name or not saved.configured:
            return False
        normalized = _normalize_exe(exe_name)
        matched = False
        try:
            with self._pulsectl.Pulse("vibranceflow-core") as pulse:
                for sink_input in pulse.sink_input_list():
                    ref = _pulse_session_ref(sink_input, self.backend_name)
                    if ref is None or _normalize_exe(ref.exe_name) != normalized:
                        continue
                    if saved.volume is not None:
                        pulse.volume_set_all_chans(sink_input, max(0.0, min(1.0, saved.volume / 100.0)))
                    if saved.muted is not None:
                        pulse.sink_input_mute(sink_input.index, bool(saved.muted))
                    matched = True
        except Exception:
            logger.debug("PulseAudio apply failed for %s", exe_name, exc_info=True)
            return False
        return matched


def create_audio_manager() -> AudioManager:
    if sys.platform == "win32":
        return WindowsAudioManager()
    if sys.platform.startswith("linux"):
        return LinuxPulseAudioManager()
    return AudioManager()


class _WindowsSessionNotification(_PycawAudioSessionNotification):
    def __init__(self, manager: WindowsAudioManager) -> None:
        super().__init__()
        self._manager = manager

    def on_session_created(self, new_session) -> None:
        self._manager.invalidate()


class _WindowsSessionEvents(_PycawAudioSessionEvents):
    def __init__(self, manager: WindowsAudioManager) -> None:
        super().__init__()
        self._manager = manager

    def on_simple_volume_changed(self, new_volume, new_mute, event_context) -> None:
        self._manager.invalidate()

    def on_state_changed(self, new_state, new_state_id) -> None:
        self._manager.invalidate()

    def on_session_disconnected(self, disconnect_reason, disconnect_reason_id) -> None:
        self._manager.invalidate()


def _simple_volume_interface(session, iface_type):
    if session is None:
        return None
    simple = getattr(session, "SimpleAudioVolume", None)
    if simple is not None:
        return simple
    if iface_type is None:
        return None
    ctl = getattr(session, "_ctl", None)
    if ctl is None:
        return None
    try:
        return ctl.QueryInterface(iface_type)
    except Exception:
        return None


def _windows_session_ref(session, backend_name: str, iface_type) -> AudioSessionRef | None:
    pid = int(getattr(session, "ProcessId", 0) or 0)
    exe_name = _exe_name_from_pid(pid)
    if not exe_name:
        return None
    simple = _simple_volume_interface(session, iface_type)
    if simple is None:
        return None
    try:
        volume = float(simple.GetMasterVolume()) * 100.0
        muted = bool(simple.GetMute())
    except Exception:
        return None
    display_name = getattr(session, "DisplayName", "") or exe_name
    state_id = int(getattr(session, "State", 0) or 0)
    return AudioSessionRef(
        backend=backend_name,
        session_id=str(getattr(session, "Identifier", "") or ""),
        instance_id=str(getattr(session, "InstanceIdentifier", "") or ""),
        process_id=pid,
        exe_name=exe_name,
        display_name=display_name,
        state=_WINDOWS_SESSION_STATES.get(state_id, f"state_{state_id}"),
        volume=max(0.0, min(100.0, volume)),
        muted=muted,
    )


def _pulse_session_ref(sink_input, backend_name: str) -> AudioSessionRef | None:
    proplist = getattr(sink_input, "proplist", {}) or {}
    exe_name = (
        proplist.get("application.process.binary")
        or proplist.get("application.name")
        or ""
    )
    if not exe_name:
        return None
    display_name = proplist.get("application.name") or exe_name
    process_id_raw = proplist.get("application.process.id") or 0
    try:
        process_id = int(process_id_raw)
    except (TypeError, ValueError):
        process_id = 0
    volume = getattr(getattr(sink_input, "volume", None), "value_flat", 1.0) * 100.0
    return AudioSessionRef(
        backend=backend_name,
        session_id=str(getattr(sink_input, "index", "")),
        instance_id=str(getattr(sink_input, "index", "")),
        process_id=process_id,
        exe_name=os.path.basename(str(exe_name)),
        display_name=str(display_name),
        state="active",
        volume=max(0.0, min(100.0, float(volume))),
        muted=bool(getattr(sink_input, "mute", False)),
    )


def _pick_display_name(sessions: tuple[AudioSessionRef, ...], fallback: str) -> str:
    for session in sessions:
        if session.display_name and session.display_name.lower() != session.exe_name.lower():
            return session.display_name
    if sessions:
        return sessions[0].display_name or sessions[0].exe_name
    return fallback


if sys.platform == "win32":
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.CloseHandle.restype = wintypes.BOOL
    _kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    _kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    _path_buffer = create_unicode_buffer(_PATH_BUF_CHARS)


def _exe_name_from_pid(pid: int) -> str | None:
    if sys.platform != "win32" or pid <= 0:
        return None
    handle = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        size = wintypes.DWORD(_PATH_BUF_CHARS)
        if not _kernel32.QueryFullProcessImageNameW(handle, 0, _path_buffer, byref(size)):
            return None
        full_path = _path_buffer.value
        return os.path.basename(full_path) if full_path else None
    finally:
        _kernel32.CloseHandle(handle)


def _normalize_exe(exe_name: str | None) -> str:
    return (exe_name or "").strip().lower()
