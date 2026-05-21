"""Windows executable icons — cache + SHGetFileInfo via ctypes."""

from __future__ import annotations

import ctypes
from ctypes import Structure, WinDLL, byref, sizeof, wintypes
from functools import lru_cache

from PIL import Image, ImageTk

_shell32 = WinDLL("shell32", use_last_error=True)
_user32 = WinDLL("user32", use_last_error=True)
_gdi32 = WinDLL("gdi32", use_last_error=True)

SHGFI_ICON = 0x000000100
SHGFI_LARGEICON = 0x0
SHGFI_SMALLICON = 0x1
SHGFI_USEFILEATTRIBUTES = 0x000000010
FILE_ATTRIBUTE_NORMAL = 0x80

ICON_SMALL = (16, 16)
ICON_LARGE = (24, 24)
ICON_PREVIEW = (48, 48)


class SHFILEINFOW(Structure):
    _fields_ = [
        ("hIcon", wintypes.HANDLE),
        ("iIcon", ctypes.c_int),
        ("dwAttributes", wintypes.DWORD),
        ("szDisplayName", wintypes.WCHAR * 260),
        ("szTypeName", wintypes.WCHAR * 80),
    ]


_shell32.SHGetFileInfoW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.POINTER(SHFILEINFOW),
    wintypes.UINT,
    wintypes.UINT,
]
_shell32.SHGetFileInfoW.restype = ctypes.c_size_t


class ICONINFO(Structure):
    _fields_ = [
        ("fIcon", wintypes.BOOL),
        ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD),
        ("hbmMask", ctypes.c_void_p),
        ("hbmColor", ctypes.c_void_p),
    ]


class BITMAP(Structure):
    _fields_ = [
        ("bmType", wintypes.LONG),
        ("bmWidth", wintypes.LONG),
        ("bmHeight", wintypes.LONG),
        ("bmWidthBytes", wintypes.LONG),
        ("bmPlanes", wintypes.WORD),
        ("bmBitsPixel", wintypes.WORD),
        ("bmBits", wintypes.LPVOID),
    ]


class BITMAPINFOHEADER(Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


BI_RGB = 0
DIB_RGB_COLORS = 0


def _configure_win32_api() -> None:
    """64-bit-safe HANDLE/HGDIOBJ signatures (default argtypes use 32-bit c_int)."""
    _user32.GetIconInfo.argtypes = [wintypes.HICON, ctypes.POINTER(ICONINFO)]
    _user32.GetIconInfo.restype = wintypes.BOOL
    _user32.DestroyIcon.argtypes = [wintypes.HICON]
    _user32.DestroyIcon.restype = wintypes.BOOL
    _user32.GetDC.argtypes = [wintypes.HWND]
    _user32.GetDC.restype = wintypes.HDC
    _user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    _user32.ReleaseDC.restype = ctypes.c_int
    _gdi32.GetObjectW.argtypes = [wintypes.HGDIOBJ, ctypes.c_int, ctypes.c_void_p]
    _gdi32.GetObjectW.restype = ctypes.c_int
    _gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    _gdi32.DeleteObject.restype = wintypes.BOOL
    _gdi32.GetDIBits.argtypes = [
        wintypes.HDC,
        wintypes.HBITMAP,
        wintypes.UINT,
        wintypes.UINT,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.UINT,
    ]
    _gdi32.GetDIBits.restype = ctypes.c_int


_configure_win32_api()


def _hicon_to_pil(hicon: int, size: tuple[int, int]) -> Image.Image | None:
    hicon_handle = wintypes.HICON(hicon)
    ii = ICONINFO()
    if not _user32.GetIconInfo(hicon_handle, byref(ii)):
        return None
    try:
        if not ii.hbmColor:
            return None
        bmp = BITMAP()
        if not _gdi32.GetObjectW(ii.hbmColor, sizeof(BITMAP), byref(bmp)):
            return None
        width, height = bmp.bmWidth, bmp.bmHeight
        bmi = BITMAPINFOHEADER()
        bmi.biSize = sizeof(BITMAPINFOHEADER)
        bmi.biWidth = width
        bmi.biHeight = -height
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = BI_RGB
        buf = (ctypes.c_ubyte * (width * height * 4))()
        hdc = _user32.GetDC(0)
        if not hdc:
            return None
        try:
            if _gdi32.GetDIBits(
                hdc,
                ii.hbmColor,
                0,
                height,
                buf,
                ctypes.byref(bmi),
                DIB_RGB_COLORS,
            ) == 0:
                return None
        finally:
            _user32.ReleaseDC(0, hdc)
        img = Image.frombuffer("RGBA", (width, height), bytes(buf), "raw", "BGRA", 0, 1)
        return img.resize(size, Image.Resampling.LANCZOS)
    finally:
        if ii.hbmColor:
            _gdi32.DeleteObject(ii.hbmColor)
        if ii.hbmMask:
            _gdi32.DeleteObject(ii.hbmMask)
        _user32.DestroyIcon(hicon_handle)


def _extract_hicon(path_or_name: str, small: bool = True) -> int | None:
    flags = SHGFI_ICON | (SHGFI_SMALLICON if small else SHGFI_LARGEICON)
    attr = FILE_ATTRIBUTE_NORMAL
    target = path_or_name
    if not path_or_name.lower().endswith(".exe"):
        target = path_or_name if "\\" in path_or_name else ""
        if not target:
            flags |= SHGFI_USEFILEATTRIBUTES
            target = ".exe"
    info = SHFILEINFOW()
    if not _shell32.SHGetFileInfoW(target, attr, byref(info), sizeof(info), flags):
        return None
    return int(info.hIcon)


@lru_cache(maxsize=256)
def get_pil_icon(path_or_name: str, size: tuple[int, int] = ICON_SMALL) -> Image.Image | None:
    hicon = _extract_hicon(path_or_name, small=size[0] <= 20)
    if not hicon:
        return None
    return _hicon_to_pil(hicon, size)


def get_ctk_image(path_or_name: str, size: tuple[int, int] = ICON_SMALL):
    """Return customtkinter.CTkImage or None."""
    import customtkinter as ctk

    pil = get_pil_icon(path_or_name, size)
    if pil is None:
        return None
    return ctk.CTkImage(light_image=pil, dark_image=pil, size=size)


def get_tk_image(path_or_name: str, size: tuple[int, int] = ICON_SMALL) -> ImageTk.PhotoImage | None:
    pil = get_pil_icon(path_or_name, size)
    if pil is None:
        return None
    return ImageTk.PhotoImage(pil)
