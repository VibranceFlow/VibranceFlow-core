"""Gerenciador de display Windows — GDI32 + NVAPI."""

from __future__ import annotations

import logging

from core.bindings.gdi_gamma import apply_primary_gamma, build_gamma_ramp, read_primary_gamma
from core.bindings.nvapi_display import NvApiDisplaySession, vibrance_percent_to_level
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
            logger.info("NVAPI inicializada (vibrance/matiz disponíveis).")
        except Exception as e:
            logger.warning("NVAPI indisponível (%s); apenas GDI32 ativo.", e)
            self._nvapi = None

        self._baseline = self.capture_current()
        logger.info(
            "Baseline capturado: vibrance=%s hue=%s",
            self._baseline.vibrance_level,
            self._baseline.hue_angle,
        )

    @property
    def nvapi_available(self) -> bool:
        return self._nvapi_ok

    def capture_current(self) -> DesktopBaseline:
        ramp = read_primary_gamma()
        vibrance = 0
        hue = 0
        if self._nvapi_ok and self._nvapi is not None:
            try:
                vibrance = self._nvapi.get_dvc().currentLevel
            except Exception as e:
                logger.warning("Falha ao ler vibrance: %s", e)
            try:
                hue = self._nvapi.get_hue().currentAngle
            except Exception as e:
                logger.warning("Falha ao ler matiz: %s", e)
        return DesktopBaseline(gamma_ramp=ramp, vibrance_level=vibrance, hue_angle=hue)

    def set_vibrance(self, percent: float) -> None:
        if not self._nvapi_ok or self._nvapi is None:
            logger.debug("set_vibrance ignorado (NVAPI off).")
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
                logger.error("Falha ao restaurar vibrance: %s", e)
            try:
                self._nvapi.set_hue(self._baseline.hue_angle)
            except Exception as e:
                logger.error("Falha ao restaurar matiz: %s", e)

    def shutdown(self) -> None:
        try:
            self.restore_defaults()
        except Exception as e:
            logger.error("Falha ao restaurar no shutdown: %s", e)
        if self._nvapi is not None:
            try:
                self._nvapi.close()
            except Exception:
                pass
            self._nvapi = None
        self._nvapi_ok = False
