"""VibranceFlow data models."""

from __future__ import annotations

from dataclasses import dataclass, field

from core.bindings.gdi_gamma import GAMMARAMP


@dataclass(frozen=True)
class AudioSettings:
    """Saved audio override for an executable."""

    volume: float | None = None
    muted: bool | None = None

    @classmethod
    def from_dict(cls, data: dict | None) -> AudioSettings:
        if not isinstance(data, dict):
            return cls()
        volume = data.get("volume")
        muted = data.get("muted")
        return cls(
            volume=None if volume is None else max(0.0, min(100.0, float(volume))),
            muted=None if muted is None else bool(muted),
        )

    def to_dict(self) -> dict:
        out: dict[str, float | bool] = {}
        if self.volume is not None:
            out["volume"] = self.volume
        if self.muted is not None:
            out["muted"] = self.muted
        return out

    @property
    def configured(self) -> bool:
        return self.volume is not None or self.muted is not None


@dataclass(frozen=True)
class AudioState:
    """Runtime audio state reported to desktop/mobile UIs."""

    available: bool = False
    volume: float = 100.0
    muted: bool = False
    session_count: int = 0
    backend: str = "none"
    display_name: str = ""
    reason: str = "no_session"

    def to_dict(self) -> dict:
        return {
            "available": self.available,
            "volume": self.volume,
            "muted": self.muted,
            "session_count": self.session_count,
            "backend": self.backend,
            "display_name": self.display_name,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ColorProfile:
    """Per-executable profile for color and optional audio overrides."""

    vibrance: float
    brightness: float
    contrast: float
    gamma: float
    hue: int = 0
    audio: AudioSettings = field(default_factory=AudioSettings)

    @classmethod
    def from_dict(cls, data: dict) -> ColorProfile:
        return cls(
            vibrance=float(data["vibrance"]),
            brightness=float(data["brightness"]),
            contrast=float(data["contrast"]),
            gamma=float(data["gamma"]),
            hue=int(data.get("hue", 0)),
            audio=AudioSettings.from_dict(data.get("audio")),
        )

    def to_dict(self) -> dict:
        return {
            "vibrance": self.vibrance,
            "brightness": self.brightness,
            "contrast": self.contrast,
            "gamma": self.gamma,
            "hue": self.hue,
        }

    def to_storage_dict(self) -> dict:
        out = self.to_dict()
        if self.hue == 0:
            out.pop("hue", None)
        if self.audio.configured:
            out["audio"] = self.audio.to_dict()
        return out


@dataclass
class DesktopBaseline:
    """State captured at startup - used by restore_defaults()."""

    gamma_ramp: GAMMARAMP
    vibrance_level: int
    hue_angle: int


@dataclass
class AppSettings:
    """Global settings (desktop profile / observer / autostart)."""

    desktop_vibrance: float = 50.0
    desktop_brightness: float = 0.0
    desktop_contrast: float = 0.0
    desktop_gamma: float = 1.0
    desktop_hue: int = 0
    observer_enabled: bool = True
    affect_primary_only: bool = False
    autostart: bool = False
    keep_remote_port_open: bool = False

    def desktop_profile(self) -> ColorProfile:
        return ColorProfile(
            vibrance=self.desktop_vibrance,
            brightness=self.desktop_brightness,
            contrast=self.desktop_contrast,
            gamma=self.desktop_gamma,
            hue=self.desktop_hue,
        )

    @classmethod
    def from_dict(cls, data: dict | None) -> AppSettings:
        if not data:
            return cls()
        return cls(
            desktop_vibrance=float(data.get("desktop_vibrance", 50)),
            desktop_brightness=float(data.get("desktop_brightness", 0)),
            desktop_contrast=float(data.get("desktop_contrast", 0)),
            desktop_gamma=float(data.get("desktop_gamma", 1.0)),
            desktop_hue=int(data.get("desktop_hue", 0)),
            observer_enabled=bool(data.get("observer_enabled", True)),
            affect_primary_only=bool(data.get("affect_primary_only", False)),
            autostart=bool(data.get("autostart", False)),
            keep_remote_port_open=bool(data.get("keep_remote_port_open", False)),
        )

    def to_dict(self) -> dict:
        return {
            "desktop_vibrance": self.desktop_vibrance,
            "desktop_brightness": self.desktop_brightness,
            "desktop_contrast": self.desktop_contrast,
            "desktop_gamma": self.desktop_gamma,
            "desktop_hue": self.desktop_hue,
            "observer_enabled": self.observer_enabled,
            "affect_primary_only": self.affect_primary_only,
            "autostart": self.autostart,
            "keep_remote_port_open": self.keep_remote_port_open,
        }
