"""GDI32 gamma ramp — brilho, contraste e gama (área de trabalho)."""

from __future__ import annotations

import ctypes
from ctypes import (
    POINTER,
    Structure,
    WinDLL,
    WINFUNCTYPE,
    byref,
    c_int,
    c_long,
    c_uint32,
    c_ushort,
    c_void_p,
    sizeof,
    wintypes,
)

MONITORINFOF_PRIMARY = 1
_primary_device: str | None = None


class GAMMARAMP(Structure):
    _fields_ = [
        ("red", c_ushort * 256),
        ("green", c_ushort * 256),
        ("blue", c_ushort * 256),
    ]


class RECT(Structure):
    _fields_ = [
        ("left", c_long),
        ("top", c_long),
        ("right", c_long),
        ("bottom", c_long),
    ]


class MONITORINFOEXW(Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


def primary_display_device() -> str:
    global _primary_device
    if _primary_device:
        return _primary_device

    user32 = WinDLL("user32", use_last_error=True)
    found: list[str] = []

    def _callback(hmonitor, _hdc, _rect, _ldata) -> int:
        info = MONITORINFOEXW()
        info.cbSize = sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hmonitor, byref(info)):
            if info.dwFlags & MONITORINFOF_PRIMARY:
                found.append(info.szDevice)
        return 1

    enum_proc = WINFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(RECT), c_void_p)(_callback)
    user32.EnumDisplayMonitors(None, None, enum_proc, 0)
    _primary_device = found[0] if found else r"\\.\DISPLAY1"
    return _primary_device


def _open_primary_gamma_dc():
    gdi32 = WinDLL("gdi32", use_last_error=True)
    gdi32.CreateDCW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        c_void_p,
    ]
    gdi32.CreateDCW.restype = wintypes.HDC
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.DeleteDC.restype = wintypes.BOOL

    device = primary_display_device()
    hdc = gdi32.CreateDCW("DISPLAY", device, None, None)
    if not hdc:
        raise OSError(f"CreateDCW falhou para {device}", ctypes.get_last_error())
    return gdi32, hdc


def copy_gamma_ramp(src: GAMMARAMP) -> GAMMARAMP:
    dst = GAMMARAMP()
    for ch in ("red", "green", "blue"):
        getattr(dst, ch)[:] = getattr(src, ch)[:]
    return dst


def read_primary_gamma() -> GAMMARAMP:
    gdi32, hdc = _open_primary_gamma_dc()
    gdi32.GetDeviceGammaRamp.argtypes = [wintypes.HDC, ctypes.POINTER(GAMMARAMP)]
    gdi32.GetDeviceGammaRamp.restype = wintypes.BOOL
    try:
        ramp = GAMMARAMP()
        if not gdi32.GetDeviceGammaRamp(hdc, byref(ramp)):
            raise OSError("GetDeviceGammaRamp falhou", ctypes.get_last_error())
        return ramp
    finally:
        gdi32.DeleteDC(hdc)


def apply_primary_gamma(ramp: GAMMARAMP) -> None:
    gdi32, hdc = _open_primary_gamma_dc()
    gdi32.SetDeviceGammaRamp.argtypes = [wintypes.HDC, ctypes.POINTER(GAMMARAMP)]
    gdi32.SetDeviceGammaRamp.restype = wintypes.BOOL
    try:
        if not gdi32.SetDeviceGammaRamp(hdc, byref(ramp)):
            raise OSError("SetDeviceGammaRamp falhou", ctypes.get_last_error())
    finally:
        gdi32.DeleteDC(hdc)


def calculate_lut_channel(
    brightness: float = 0.5,
    contrast: float = 0.5,
    gamma: float = 1.0,
) -> list[int]:
    """LUT 256 pontos — algoritmo do Painel NVIDIA (NvAPIWrapper #20)."""
    data_points = 256
    gamma = max(0.4, min(2.8, gamma))
    contrast = (max(0.0, min(1.0, contrast)) - 0.5) * 2.0
    brightness = (max(0.0, min(1.0, brightness)) - 0.5) * 2.0

    offset = contrast * -25.4 if contrast > 0 else contrast * -32.0
    range_val = (data_points - 1) + offset * 2.0
    offset += brightness * (range_val / 5.0)

    result: list[int] = []
    for i in range(data_points):
        factor = (i + offset) / range_val
        factor = factor ** (1.0 / gamma)
        factor = max(0.0, min(1.0, factor))
        result.append(int(round(factor * 65535)))
    return result


def panel_percent_to_slider(percent_offset: float) -> float:
    """'+42%' do painel → entrada 0–1 (0.5 = neutro)."""
    return max(0.0, min(1.0, 0.5 + percent_offset / 100.0))


def build_gamma_ramp(brightness_pct: float, contrast_pct: float, gamma_val: float) -> GAMMARAMP:
    b = panel_percent_to_slider(brightness_pct)
    c = panel_percent_to_slider(contrast_pct)
    lut = calculate_lut_channel(b, c, gamma_val)
    ramp = GAMMARAMP()
    for i in range(256):
        ramp.red[i] = lut[i]
        ramp.green[i] = lut[i]
        ramp.blue[i] = lut[i]
    return ramp
