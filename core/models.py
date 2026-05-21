"""Modelos de dados do LuminaSync."""

from __future__ import annotations

from dataclasses import dataclass

from core.bindings.gdi_gamma import GAMMARAMP


@dataclass(frozen=True)
class ColorProfile:
    """Perfil de cor para um executável (unidades estilo Painel NVIDIA)."""

    vibrance: float
    brightness: float
    contrast: float
    gamma: float
    hue: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> ColorProfile:
        return cls(
            vibrance=float(data["vibrance"]),
            brightness=float(data["brightness"]),
            contrast=float(data["contrast"]),
            gamma=float(data["gamma"]),
            hue=int(data.get("hue", 0)),
        )

    def to_dict(self) -> dict:
        out = {
            "vibrance": self.vibrance,
            "brightness": self.brightness,
            "contrast": self.contrast,
            "gamma": self.gamma,
        }
        if self.hue != 0:
            out["hue"] = self.hue
        return out


@dataclass
class DesktopBaseline:
    """Estado capturado na inicialização — usado em restore_defaults()."""

    gamma_ramp: GAMMARAMP
    vibrance_level: int
    hue_angle: int


@dataclass
class AppSettings:
    """Configurações globais (área de trabalho / observer)."""

    desktop_vibrance: float = 50.0
    desktop_brightness: float = 0.0
    desktop_contrast: float = 0.0
    desktop_gamma: float = 1.0
    desktop_hue: int = 0
    observer_enabled: bool = True
    affect_primary_only: bool = False
    autostart: bool = False

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
        }
