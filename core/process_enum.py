"""Lista processos em execução — Toolhelp32 via ctypes (sem psutil)."""

from __future__ import annotations

import ctypes
from ctypes import Structure, WinDLL, byref, c_uint32, c_void_p, create_unicode_buffer, sizeof, wintypes
from dataclasses import dataclass

TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

_kernel32 = WinDLL("kernel32", use_last_error=True)

_kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
_kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
_kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, c_void_p]
_kernel32.Process32FirstW.restype = wintypes.BOOL
_kernel32.Process32NextW.argtypes = [wintypes.HANDLE, c_void_p]
_kernel32.Process32NextW.restype = wintypes.BOOL
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL
_kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_kernel32.OpenProcess.restype = wintypes.HANDLE
_kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
_kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL

_PATH_BUF = create_unicode_buffer(32768)


class PROCESSENTRY32W(Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", c_void_p),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


@dataclass(frozen=True)
class RunningProcess:
    name: str
    pid: int
    path: str = ""


def resolve_process_path(pid: int) -> str:
    handle = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        if _kernel32.QueryFullProcessImageNameW(handle, 0, _PATH_BUF, byref(size)):
            return _PATH_BUF.value or ""
    finally:
        _kernel32.CloseHandle(handle)
    return ""


def list_running_processes(*, resolve_paths: bool = False) -> list[RunningProcess]:
    """
    Lista processos .exe únicos. Por padrão NÃO resolve caminho completo (rápido).
    """
    snap = _kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == wintypes.HANDLE(-1).value:
        raise OSError("CreateToolhelp32Snapshot falhou", ctypes.get_last_error())

    entry = PROCESSENTRY32W()
    entry.dwSize = sizeof(PROCESSENTRY32W)
    seen: dict[str, RunningProcess] = {}

    try:
        if not _kernel32.Process32FirstW(snap, byref(entry)):
            return []

        while True:
            name = entry.szExeFile
            if name and name.lower().endswith(".exe"):
                key = name.lower()
                if key not in seen:
                    path = ""
                    if resolve_paths:
                        path = resolve_process_path(entry.th32ProcessID) or name
                    seen[key] = RunningProcess(
                        name=name,
                        pid=entry.th32ProcessID,
                        path=path,
                    )
            if not _kernel32.Process32NextW(snap, byref(entry)):
                break
    finally:
        _kernel32.CloseHandle(snap)

    return sorted(seen.values(), key=lambda p: p.name.lower())
