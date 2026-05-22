"""Fernet encryption for remote WebSocket payloads."""

from __future__ import annotations

import base64
import secrets

from cryptography.fernet import Fernet, InvalidToken


def generate_key() -> str:
    """URL-safe base64 Fernet key for QR pairing."""
    return Fernet.generate_key().decode("ascii")


def _fernet(key: str) -> Fernet:
    return Fernet(key.encode("ascii"))


def _b64url_decode(wire: str) -> bytes:
    """Accept frames from mobile (padding optional) or Python (padded)."""
    s = wire.strip()
    pad = (-len(s)) % 4
    if pad:
        s += "=" * pad
    return base64.urlsafe_b64decode(s.encode("ascii"))


def encrypt_json(key: str, plaintext: str) -> str:
    token = _fernet(key).encrypt(plaintext.encode("utf-8"))
    return base64.urlsafe_b64encode(token).decode("ascii")


def decrypt_json(key: str, ciphertext_b64: str) -> str:
    try:
        raw = _b64url_decode(ciphertext_b64)
        return _fernet(key).decrypt(raw).decode("utf-8")
    except (InvalidToken, ValueError) as e:
        raise ValueError("decrypt failed") from e


def random_message_id() -> str:
    return secrets.token_hex(8)
