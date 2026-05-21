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


def get_lan_ipv4() -> str:
    """Best-effort primary LAN IPv4 (RFC1918 / link-local)."""
    candidates: list[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if _is_private_ipv4(ip) and ip not in candidates:
                candidates.append(ip)
    except OSError:
        pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if _is_private_ipv4(ip) and ip not in candidates:
                candidates.insert(0, ip)
    except OSError:
        pass

    if candidates:
        return candidates[0]
    return "127.0.0.1"


def build_pairing_payload(host: str, port: int, key: str) -> dict[str, Any]:
    return {
        "v": PROTOCOL_VERSION,
        "host": host,
        "port": port,
        "key": key,
    }


def pairing_json(host: str, port: int, key: str) -> str:
    return json.dumps(build_pairing_payload(host, port, key), separators=(",", ":"))
