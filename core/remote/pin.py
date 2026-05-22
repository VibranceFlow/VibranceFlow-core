"""Short-lived 6-digit LAN pairing code (fallback when QR/camera unavailable)."""

from __future__ import annotations

import json
import secrets
import time
from typing import Any

from core.remote.pairing import PROTOCOL_VERSION

PIN_TTL_SEC = 900
MAX_ATTEMPTS = 8
LOCKOUT_SEC = 60


class PairingPinManager:
    def __init__(self) -> None:
        self._pin = ""
        self._expires_at = 0.0
        self._attempts = 0
        self._locked_until = 0.0

    def regenerate(self) -> str:
        self._pin = f"{secrets.randbelow(1_000_000):06d}"
        self._expires_at = time.monotonic() + PIN_TTL_SEC
        self._attempts = 0
        self._locked_until = 0.0
        return self._pin

    @property
    def code(self) -> str:
        return self._pin

    def is_active(self) -> bool:
        return bool(self._pin) and time.monotonic() <= self._expires_at

    def verify(self, pin: str) -> bool:
        now = time.monotonic()
        if now < self._locked_until:
            return False
        if not self.is_active():
            return False
        cleaned = "".join(c for c in pin.strip() if c.isdigit())
        if len(cleaned) != 6:
            self._register_fail(now)
            return False
        if secrets.compare_digest(cleaned, self._pin):
            return True
        self._register_fail(now)
        return False

    def consume(self) -> None:
        self._pin = ""
        self._expires_at = 0.0
        self._attempts = 0

    def _register_fail(self, now: float) -> None:
        self._attempts += 1
        if self._attempts >= MAX_ATTEMPTS:
            self._locked_until = now + LOCKOUT_SEC
            self._attempts = 0


def parse_pair_request(raw: str) -> dict[str, Any] | None:
    """Plaintext pre-auth pair frame, or None if not a pair request."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    if data.get("v") != PROTOCOL_VERSION or data.get("cmd") != "pair":
        return None
    pin = data.get("pin")
    if not isinstance(pin, str):
        return None
    return data


def build_pair_response(
    *,
    ok: bool,
    host: str | None = None,
    port: int | None = None,
    key: str | None = None,
    error: str | None = None,
) -> str:
    body: dict[str, Any] = {"v": PROTOCOL_VERSION, "ok": ok}
    if ok and host is not None and port is not None and key is not None:
        body["host"] = host
        body["port"] = port
        body["key"] = key
    if error:
        body["error"] = error
    return json.dumps(body, separators=(",", ":"))
