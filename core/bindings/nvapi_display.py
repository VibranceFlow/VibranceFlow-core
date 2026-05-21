"""NVAPI — Digital Vibrance e matiz (ctypes / nvapi64.dll)."""

from __future__ import annotations

import ctypes
import sys
from ctypes import (
    Structure,
    WinDLL,
    byref,
    c_int,
    c_uint,
    c_uint32,
    c_void_p,
    sizeof,
)

NVAPI_OK = 0
NVAPI_END_ENUMERATION = -7

NVAPI_ID = {
    "Initialize": 0x0150E828,
    "Unload": 0x0D22BDD7E,
    "EnumNvidiaDisplayHandle": 0x9ABDD40D,
    "GetDVCInfo": 0x4085DE45,
    "SetDVCLevel": 0x172409B4,
    "GetHUEInfo": 0x95B64341,
    "SetHUEAngle": 0xF5A0F22C,
}


class NV_DISPLAY_DVC_INFO(Structure):
    _fields_ = [
        ("version", c_uint32),
        ("currentLevel", c_int),
        ("minLevel", c_int),
        ("maxLevel", c_int),
    ]


class NV_DISPLAY_HUE_INFO(Structure):
    _fields_ = [
        ("version", c_uint32),
        ("currentAngle", c_int),
        ("defaultAngle", c_int),
    ]


def _dvc_version() -> int:
    return sizeof(NV_DISPLAY_DVC_INFO) | 0x10000


def _hue_version() -> int:
    return sizeof(NV_DISPLAY_HUE_INFO) | 0x10000


def struct_bits() -> int:
    return 64 if sys.maxsize > 2**32 else 32


def vibrance_percent_to_level(info: NV_DISPLAY_DVC_INFO, percent: float) -> int:
    """Converte vibrance 0–100% para nível NVAPI min..max."""
    ratio = max(0.0, min(100.0, percent)) / 100.0
    span = info.maxLevel - info.minLevel
    return min(info.maxLevel, info.minLevel + int(round(span * ratio)))


class NvApiDisplaySession:
    """Sessão NVAPI de longa duração (DVC + Hue)."""

    def __init__(self) -> None:
        self._dll: WinDLL | None = None
        self._qi = None
        self._fns: dict[str, ctypes._CFuncPtr] = {}
        self._display_handle: int | None = None

    def _bind(self, name: str, proto, api_id: int | None = None) -> None:
        assert self._qi is not None
        fid = api_id if api_id is not None else NVAPI_ID[name]
        ptr = self._qi(fid)
        if not ptr:
            raise RuntimeError(f"nvapi_QueryInterface retornou NULL para {name}")
        self._fns[name] = proto(ptr)

    def open(self) -> None:
        if struct_bits() != 64:
            raise RuntimeError("LuminaSync requer Python 64-bit (nvapi64.dll).")
        for path in ("nvapi64", "nvapi"):
            try:
                self._dll = WinDLL(path)
                break
            except OSError:
                self._dll = None
        if self._dll is None:
            raise RuntimeError("nvapi64.dll não encontrada. Instale o driver NVIDIA.")

        self._qi = self._dll.nvapi_QueryInterface
        self._qi.argtypes = [c_uint]
        self._qi.restype = c_void_p

        NVAPI = ctypes.WINFUNCTYPE(c_int)
        self._bind("Initialize", NVAPI)
        self._bind("Unload", NVAPI)

        ENUM = ctypes.WINFUNCTYPE(c_int, c_int, ctypes.POINTER(c_void_p))
        self._bind("EnumNvidiaDisplayHandle", ENUM)

        GET_DVC = ctypes.WINFUNCTYPE(
            c_int, c_void_p, c_uint32, ctypes.POINTER(NV_DISPLAY_DVC_INFO)
        )
        self._bind("GetDVCInfo", GET_DVC)

        SET_DVC = ctypes.WINFUNCTYPE(c_int, c_void_p, c_uint32, c_int)
        self._bind("SetDVCLevel", SET_DVC)

        GET_HUE = ctypes.WINFUNCTYPE(
            c_int, c_void_p, c_uint32, ctypes.POINTER(NV_DISPLAY_HUE_INFO)
        )
        self._bind("GetHUEInfo", GET_HUE, NVAPI_ID["GetHUEInfo"])

        SET_HUE = ctypes.WINFUNCTYPE(c_int, c_void_p, c_uint32, c_int)
        self._bind("SetHUEAngle", SET_HUE, NVAPI_ID["SetHUEAngle"])

        st = self._fns["Initialize"]()
        if st != NVAPI_OK:
            raise RuntimeError(f"NvAPI_Initialize falhou: {st}")

        self._display_handle = self.primary_display_handle()

    def close(self) -> None:
        if "Unload" in self._fns:
            try:
                self._fns["Unload"]()
            except Exception:
                pass
        self._display_handle = None

    @property
    def display_handle(self) -> int:
        if self._display_handle is None:
            raise RuntimeError("Sessão NVAPI não aberta.")
        return self._display_handle

    def primary_display_handle(self) -> int:
        handle = c_void_p()
        st = self._fns["EnumNvidiaDisplayHandle"](0, byref(handle))
        if st == NVAPI_END_ENUMERATION or not handle.value:
            raise RuntimeError("Nenhum display NVIDIA enumerado.")
        if st != NVAPI_OK:
            raise RuntimeError(f"EnumNvidiaDisplayHandle falhou: {st}")
        return handle.value

    def get_dvc(self) -> NV_DISPLAY_DVC_INFO:
        info = NV_DISPLAY_DVC_INFO()
        info.version = _dvc_version()
        st = self._fns["GetDVCInfo"](self.display_handle, 0, byref(info))
        if st != NVAPI_OK:
            raise RuntimeError(f"NvAPI_GetDVCInfo falhou: {st}")
        return info

    def set_dvc(self, level: int) -> None:
        st = self._fns["SetDVCLevel"](self.display_handle, 0, int(level))
        if st != NVAPI_OK:
            raise RuntimeError(f"NvAPI_SetDVCLevel({level}) falhou: {st}")

    def get_hue(self) -> NV_DISPLAY_HUE_INFO:
        info = NV_DISPLAY_HUE_INFO()
        info.version = _hue_version()
        st = self._fns["GetHUEInfo"](self.display_handle, 0, byref(info))
        if st != NVAPI_OK:
            raise RuntimeError(f"NvAPI_GetHUEInfo falhou: {st}")
        return info

    def set_hue(self, angle: int) -> None:
        st = self._fns["SetHUEAngle"](self.display_handle, 0, int(angle) % 360)
        if st != NVAPI_OK:
            raise RuntimeError(f"NvAPI_SetHUEAngle({angle}) falhou: {st}")
