"""Profile persistence at %APPDATA%/VibranceFlow/profiles.json."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from core.models import AppSettings, ColorProfile

logger = logging.getLogger(__name__)

PROFILE_VERSION = 2


class ProfileSaveError(OSError):
    """Raised when profiles.json cannot be written."""


def default_profiles_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise OSError("APPDATA environment variable is not set.")
    vibrance = Path(appdata) / "VibranceFlow" / "profiles.json"
    legacy = Path(appdata) / "LuminaSync" / "profiles.json"
    if vibrance.exists():
        return vibrance
    if legacy.exists():
        return legacy
    return vibrance


def _vibranceflow_profiles_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise OSError("APPDATA environment variable is not set.")
    return Path(appdata) / "VibranceFlow" / "profiles.json"


def _is_legacy_luminasync_path(path: Path) -> bool:
    parts = {p.lower() for p in path.parts}
    return "luminasync" in parts and "vibranceflow" not in parts


class ProfileManager:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or default_profiles_path()
        self._profiles: dict[str, ColorProfile] = {}
        self._settings = AppSettings()
        self._file_mtime: float = 0.0
        self._maybe_migrate_legacy_path()
        self._load()

    def _maybe_migrate_legacy_path(self) -> None:
        if not _is_legacy_luminasync_path(self._path):
            return
        target = _vibranceflow_profiles_path()
        if target.exists():
            logger.info(
                "Using %s (legacy LuminaSync file also present at %s)",
                target,
                self._path,
            )
            self._path = target
            return
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self._path.read_bytes())
            logger.info("Migrated profiles from %s to %s", self._path, target)
            self._path = target
        except OSError as e:
            logger.warning("Could not migrate profiles to %s: %s", target, e)

    @property
    def path(self) -> Path:
        return self._path

    def _load(self) -> None:
        if not self._path.exists():
            self._profiles = {}
            self._file_mtime = 0.0
            return
        try:
            self._file_mtime = self._path.stat().st_mtime
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to read %s: %s", self._path, e)
            self._profiles = {}
            return

        if isinstance(raw, dict):
            self._settings = AppSettings.from_dict(raw.get("settings"))
            profiles_raw = raw.get("profiles", {})
        else:
            profiles_raw = {}

        self._profiles = {}
        for exe, data in profiles_raw.items():
            if isinstance(data, dict):
                try:
                    self._profiles[exe] = ColorProfile.from_dict(data)
                except (KeyError, TypeError, ValueError) as e:
                    logger.warning("Invalid profile for %s: %s", exe, e)

    def save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": PROFILE_VERSION,
                "settings": self._settings.to_dict(),
                "profiles": {exe: p.to_storage_dict() for exe, p in self._profiles.items()},
            }
            self._path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            if self._path.exists():
                self._file_mtime = self._path.stat().st_mtime
        except OSError as e:
            logger.error("Failed to save profiles to %s: %s", self._path, e)
            raise ProfileSaveError(str(e)) from e

    def reload_if_stale(self) -> bool:
        """Reload profiles.json when another writer (or remote) changed it on disk."""
        if not self._path.exists():
            return False
        try:
            mtime = self._path.stat().st_mtime
        except OSError:
            return False
        if mtime <= self._file_mtime + 1e-6:
            return False
        self._load()
        return True

    def get(self, exe_name: str) -> ColorProfile | None:
        if not exe_name:
            return None
        key = self._normalize_key(exe_name)
        for stored, profile in self._profiles.items():
            if stored.lower() == key:
                return profile
        return None

    def list_executables(self) -> list[str]:
        return sorted(self._profiles.keys())

    def upsert(self, exe_name: str, profile: ColorProfile) -> None:
        self._profiles[exe_name] = profile
        self.save()

    def remove(self, exe_name: str) -> bool:
        key = self._normalize_key(exe_name)
        for stored in list(self._profiles.keys()):
            if stored.lower() == key:
                del self._profiles[stored]
                self.save()
                return True
        return False

    def reload(self) -> None:
        self._load()

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def update_settings(self, settings: AppSettings) -> None:
        self._settings = settings
        self.save()

    def desktop_profile(self) -> ColorProfile:
        return self._settings.desktop_profile()

    @staticmethod
    def _normalize_key(exe_name: str) -> str:
        return exe_name.strip().lower()
