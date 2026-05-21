"""JSON envelope validation for remote commands."""

from __future__ import annotations

import json
from typing import Any

from core.remote.pairing import PROTOCOL_VERSION

MAX_JSON_BYTES = 8192

ALLOWED_COMMANDS = frozenset(
    {"ping", "get_state", "set_sliders", "set_observer", "reset_profile"}
)


class ProtocolError(Exception):
    def __init__(self, message: str, *, code: str = "protocol_error") -> None:
        super().__init__(message)
        self.code = code


def parse_request(raw: str) -> dict[str, Any]:
    if len(raw.encode("utf-8")) > MAX_JSON_BYTES:
        raise ProtocolError("payload too large", code="too_large")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ProtocolError("invalid json", code="invalid_json") from e
    if not isinstance(data, dict):
        raise ProtocolError("expected object", code="invalid_shape")
    if data.get("v") != PROTOCOL_VERSION:
        raise ProtocolError("unsupported protocol version", code="bad_version")
    cmd = data.get("cmd")
    if not isinstance(cmd, str) or cmd not in ALLOWED_COMMANDS:
        raise ProtocolError("unknown command", code="unknown_cmd")
    msg_id = data.get("id")
    if msg_id is not None and not isinstance(msg_id, str):
        raise ProtocolError("invalid id", code="invalid_id")
    payload = data.get("payload")
    if payload is not None and not isinstance(payload, dict):
        raise ProtocolError("payload must be object", code="invalid_payload")
    return data


def build_response(
    *,
    ok: bool,
    msg_id: str | None = None,
    state: dict[str, Any] | None = None,
    error: str | None = None,
) -> str:
    body: dict[str, Any] = {"v": PROTOCOL_VERSION, "ok": ok}
    if msg_id:
        body["id"] = msg_id
    if state is not None:
        body["state"] = state
    if error:
        body["error"] = error
    return json.dumps(body, separators=(",", ":"))
