#!/usr/bin/env python3
"""Headless smoke test: remote WebSocket server starts and accepts ping."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import threading
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.remote.crypto import decrypt_json, encrypt_json, generate_key  # noqa: E402
from core.remote.handlers import RemoteCommandHandler  # noqa: E402
from core.remote.health import RemoteStartError, probe_port_listening, verify_remote_dependencies  # noqa: E402
from core.remote.pairing import DEFAULT_PORT  # noqa: E402
from core.remote.server import RemoteServer  # noqa: E402


def _mock_handler() -> RemoteCommandHandler:
    def get_state() -> dict:
        return {
            "observer_enabled": False,
            "active_exe": None,
            "sliders": {},
            "audio": {},
            "programs": [],
        }

    return RemoteCommandHandler(
        get_state=get_state,
        set_sliders=lambda _p, _e: None,
        set_audio=lambda _a, _e: None,
        set_observer=lambda _b: None,
        reset_profile=lambda _e: None,
    )


def _run_sync_on_main(fn) -> None:
    fn()


async def _ping_once(host: str, port: int, key: str) -> None:
    import websockets

    uri = f"ws://{host}:{port}"
    msg_id = uuid.uuid4().hex[:8]
    body = json.dumps({"v": 1, "id": msg_id, "cmd": "ping"}, separators=(",", ":"))
    wire = encrypt_json(key, body)
    async with websockets.connect(uri, max_size=16384, open_timeout=5) as ws:
        await ws.send(wire)
        raw = await asyncio.wait_for(ws.recv(), timeout=5)
        plain = decrypt_json(key, raw if isinstance(raw, str) else raw.decode("utf-8"))
        data = json.loads(plain)
        if not data.get("ok"):
            raise RuntimeError(f"ping failed: {data}")


def run_boot_test(port: int = DEFAULT_PORT, timeout: float = 5.0) -> None:
    dep_err = verify_remote_dependencies()
    if dep_err:
        raise RemoteStartError(dep_err)

    server = RemoteServer(_mock_handler(), port=port, on_main_thread=_run_sync_on_main)
    try:
        server.start()
        if not server.wait_until_ready(timeout):
            err = server.last_start_error or "server did not listen in time"
            raise RemoteStartError(err)
        if not probe_port_listening("127.0.0.1", port):
            raise RemoteStartError(f"port {port} not accepting connections on loopback")

        key = str(server.pairing_payload.get("key", ""))
        if not key:
            raise RemoteStartError("pairing key missing from server payload")
        asyncio.run(_ping_once("127.0.0.1", port, key))
        print(f"OK remote boot test on 127.0.0.1:{port}")
    finally:
        server.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test VibranceFlow remote WebSocket boot")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    try:
        run_boot_test(port=args.port, timeout=args.timeout)
        return 0
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
