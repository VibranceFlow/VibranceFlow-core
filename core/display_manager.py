"""Windows display manager — GDI32 + NVAPI."""

from __future__ import annotations

import logging

from core.bindings.gdi_gamma import apply_primary_gamma, build_gamma_ramp, read_primary_gamma
from core.bindings.nvapi_display import (
    NvApiDisplaySession,
    vibrance_level_to_percent,
    vibrance_percent_to_level,
)
from core.models import ColorProfile, DesktopBaseline

logger = logging.getLogger(__name__)


class WindowsDisplayManager:
    def __init__(self) -> None:
        self._nvapi: NvApiDisplaySession | None = None
        self._nvapi_ok = False
        try:
            self._nvapi = NvApiDisplaySession()
            self._nvapi.open()
            self._nvapi_ok = True
            logger.info("NVAPI initialized (vibrance/hue available).")
        except Exception as e:
            logger.warning("NVAPI unavailable (%s); GDI32 only.", e)
            self._nvapi = None

        self._baseline = self.capture_current()
        self._gpu_default_profile = self._baseline_to_profile(self._baseline)
        logger.info(
            "Baseline captured: vibrance=%s hue=%s",
            self._baseline.vibrance_level,
            self._baseline.hue_angle,
        )

    @property
    def nvapi_available(self) -> bool:
        return self._nvapi_ok

    @property
    def gpu_default_profile(self) -> ColorProfile:
        """Color profile matching GPU/desktop state at startup."""
        return self._gpu_default_profile

    def _baseline_to_profile(self, baseline: DesktopBaseline) -> ColorProfile:
        vibrance = 50.0
        if self._nvapi_ok and self._nvapi is not None:
            try:
                info = self._nvapi.get_dvc()
                vibrance = vibrance_level_to_percent(info, baseline.vibrance_level)
            except Exception as e:
                logger.warning("Could not map baseline vibrance: %s", e)
        return ColorProfile(
            vibrance=vibrance,
            brightness=0.0,
            contrast=0.0,
            gamma=1.0,
            hue=int(baseline.hue_angle),
        )

    def capture_current(self) -> DesktopBaseline:
        ramp = read_primary_gamma()
        vibrance = 0
        hue = 0
        if self._nvapi_ok and self._nvapi is not None:
            try:
                vibrance = self._nvapi.get_dvc().currentLevel
            except Exception as e:
                logger.warning("Failed to read vibrance: %s", e)
            try:
                hue = self._nvapi.get_hue().currentAngle
            except Exception as e:
                logger.warning("Failed to read hue: %s", e)
        return DesktopBaseline(gamma_ramp=ramp, vibrance_level=vibrance, hue_angle=hue)

    def set_vibrance(self, percent: float) -> None:
        if not self._nvapi_ok or self._nvapi is None:
            logger.debug("set_vibrance skipped (NVAPI off).")
            return
        info = self._nvapi.get_dvc()
        level = vibrance_percent_to_level(info, percent)
        self._nvapi.set_dvc(level)

    def set_hue(self, degrees: int) -> None:
        if not self._nvapi_ok or self._nvapi is None:
            return
        self._nvapi.set_hue(degrees)

    def set_gamma_ramp(
        self,
        brightness_pct: float,
        contrast_pct: float,
        gamma: float,
    ) -> None:
        ramp = build_gamma_ramp(brightness_pct, contrast_pct, gamma)
        apply_primary_gamma(ramp)

    def apply_profile(self, profile: ColorProfile) -> None:
        self.set_gamma_ramp(profile.brightness, profile.contrast, profile.gamma)
        self.set_vibrance(profile.vibrance)
        self.set_hue(profile.hue)

    def restore_defaults(self) -> None:
        apply_primary_gamma(self._baseline.gamma_ramp)
        if self._nvapi_ok and self._nvapi is not None:
            try:
                self._nvapi.set_dvc(self._baseline.vibrance_level)
            except Exception as e:
                logger.error("Failed to restore vibrance: %s", e)
            try:
                self._nvapi.set_hue(self._baseline.hue_angle)
            except Exception as e:
                logger.error("Failed to restore hue: %s", e)

    def shutdown(self) -> None:
        try:
            self.restore_defaults()
        except Exception as e:
            logger.error("Failed to restore on shutdown: %s", e)
        if self._nvapi is not None:
            try:
                self._nvapi.close()
            except Exception:
                pass
            self._nvapi = None
        self._nvapi_ok = False
