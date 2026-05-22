"""LAN discovery and QR pairing payload."""

from __future__ import annotations

import ipaddress
import json
import socket
from typing import Any

DEFAULT_PORT = 8765
PROTOCOL_VERSION = 1


def _is_private_ipv4(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
        return ip.is_private or ip.is_link_local
    except ValueError:
        return False


def _collect_private_ipv4_candidates() -> list[str]:
    """Prefer default-route interface; never use loopback for QR pairing."""
    ordered: list[str] = []
    seen: set[str] = set()

    def add(ip: str, *, front: bool = False) -> None:
        if not _is_private_ipv4(ip) or ip.startswith("127."):
            return
        if ip in seen:
            return
        seen.add(ip)
        if front:
            ordered.insert(0, ip)
        else:
            ordered.append(ip)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            add(s.getsockname()[0], front=True)
    except OSError:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            add(info[4][0])
    except OSError:
        pass

    return ordered


def get_lan_ipv4() -> str:
    """Best-effort primary LAN IPv4 for QR (RFC1918 / link-local, never 127.0.0.1)."""
    candidates = _collect_private_ipv4_candidates()
    if candidates:
        return candidates[0]
    return "127.0.0.1"


def get_lan_ipv4_candidates() -> list[str]:
    """All usable LAN IPv4 addresses (for UI hints)."""
    return _collect_private_ipv4_candidates()


def build_pairing_payload(host: str, port: int, key: str) -> dict[str, Any]:
    return {
        "v": PROTOCOL_VERSION,
        "host": host,
        "port": port,
        "key": key,
    }


def pairing_json(host: str, port: int, key: str) -> str:
    return json.dumps(build_pairing_payload(host, port, key), separators=(",", ":"))
