"""Monitor de janela em foreground — ctypes puro, sem psutil."""

from __future__ import annotations

import ctypes
import os
from ctypes import byref, c_uint32, c_void_p, create_unicode_buffer, wintypes

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_PATH_BUF_CHARS = 32768

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_user32.GetForegroundWindow.argtypes = []
_user32.GetForegroundWindow.restype = wintypes.HWND

_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(c_uint32)]
_user32.GetWindowThreadProcessId.restype = c_uint32

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
_size_dw = wintypes.DWORD(_PATH_BUF_CHARS)


def get_foreground_executable() -> str | None:
    """
    Retorna o nome do executável (.exe) da janela em foreground, ou None.
    """
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return None

    pid = c_uint32()
    _user32.GetWindowThreadProcessId(hwnd, byref(pid))
    if not pid.value:
        return None

    handle = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return None

    try:
        size = wintypes.DWORD(_PATH_BUF_CHARS)
        if not _kernel32.QueryFullProcessImageNameW(handle, 0, _path_buffer, byref(size)):
            return None
        full_path = _path_buffer.value
        if not full_path:
            return None
        return os.path.basename(full_path)
    finally:
        _kernel32.CloseHandle(handle)
