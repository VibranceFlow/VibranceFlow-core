"""Remote command handlers - run on the main thread via bridge."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from core.models import AudioSettings, ColorProfile
from core.profile_manager import ProfileSaveError
from core.remote.protocol import ProtocolError, build_response, parse_request

logger = logging.getLogger(__name__)

RATE_LIMIT_INTERVAL = 0.02  # ~50 msg/s max per connection


class RemoteCommandHandler:
    def __init__(
        self,
        *,
        get_state: Callable[[], dict[str, Any]],
        set_sliders: Callable[[ColorProfile, str | None], None],
        set_audio: Callable[[AudioSettings, str | None], None],
        set_observer: Callable[[bool], None],
        reset_profile: Callable[[str | None], None],
    ) -> None:
        self._get_state = get_state
        self._set_sliders = set_sliders
        self._set_audio = set_audio
        self._set_observer = set_observer
        self._reset_profile = reset_profile
        self._last_msg_at = 0.0

    def _rate_limit(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_msg_at
        if elapsed < RATE_LIMIT_INTERVAL:
            time.sleep(RATE_LIMIT_INTERVAL - elapsed)
        self._last_msg_at = time.monotonic()

    def handle(self, plaintext: str) -> str:
        self._rate_limit()
        try:
            req = parse_request(plaintext)
        except ProtocolError as e:
            return build_response(ok=False, error=str(e), error_code=e.code)

        msg_id = req.get("id")
        cmd = req["cmd"]
        payload = req.get("payload") or {}

        try:
            if cmd == "ping":
                return build_response(ok=True, msg_id=msg_id, state={"pong": True})

            if cmd == "get_state":
                return build_response(ok=True, msg_id=msg_id, state=self._get_state())

            if cmd == "set_sliders":
                profile = _profile_from_payload(payload)
                target = payload.get("exe")
                if target is not None and not isinstance(target, str):
                    raise ProtocolError("exe must be string")
                self._set_sliders(profile, target)
                return build_response(ok=True, msg_id=msg_id, state=self._get_state())

            if cmd == "set_audio":
                audio = _audio_from_payload(payload)
                target = payload.get("exe")
                if target is not None and not isinstance(target, str):
                    raise ProtocolError("exe must be string")
                self._set_audio(audio, target)
                return build_response(ok=True, msg_id=msg_id, state=self._get_state())

            if cmd == "set_observer":
                enabled = _as_bool(payload.get("enabled"), field="enabled")
                self._set_observer(enabled)
                return build_response(ok=True, msg_id=msg_id, state=self._get_state())

            if cmd == "reset_profile":
                target = payload.get("exe")
                if target is not None and not isinstance(target, str):
                    raise ProtocolError("exe must be string")
                self._reset_profile(target)
                return build_response(ok=True, msg_id=msg_id, state=self._get_state())

            return build_response(ok=False, msg_id=msg_id, error="unhandled command")
        except ProtocolError as e:
            return build_response(
                ok=False, msg_id=msg_id, error=str(e), error_code=e.code
            )
        except ProfileSaveError as e:
            logger.error("remote command could not persist profiles: %s", e)
            return build_response(
                ok=False,
                msg_id=msg_id,
                error="profile save failed",
                error_code="profile_save_failed",
            )
        except Exception:
            logger.exception("remote command failed: %s", cmd)
            return build_response(
                ok=False,
                msg_id=msg_id,
                error="internal error",
                error_code="internal_error",
            )


def _as_bool(value: Any, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    raise ProtocolError(f"{field} must be boolean")


def _profile_from_payload(payload: dict[str, Any]) -> ColorProfile:
    required = ("vibrance", "brightness", "contrast", "gamma")
    for key in required:
        if key not in payload:
            raise ProtocolError(f"missing {key}")
    try:
        return ColorProfile(
            vibrance=float(payload["vibrance"]),
            brightness=float(payload["brightness"]),
            contrast=float(payload["contrast"]),
            gamma=float(payload["gamma"]),
            hue=int(payload.get("hue", 0)),
        )
    except (TypeError, ValueError) as e:
        raise ProtocolError("invalid slider values") from e


def _audio_from_payload(payload: dict[str, Any]) -> AudioSettings:
    has_volume = "volume" in payload
    has_muted = "muted" in payload
    if not has_volume and not has_muted:
        raise ProtocolError("missing audio fields")
    try:
        volume = None if not has_volume else max(0.0, min(100.0, float(payload["volume"])))
    except (TypeError, ValueError) as e:
        raise ProtocolError("invalid audio volume") from e
    muted = None
    if has_muted:
        muted = _as_bool(payload.get("muted"), field="muted")
    return AudioSettings(volume=volume, muted=muted)
