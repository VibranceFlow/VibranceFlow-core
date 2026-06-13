#!/usr/bin/env python3
"""Simulate mobile PIN pairing (plaintext WS) - same as pairClient.ts."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.remote.pairing import DEFAULT_PORT  # noqa: E402


async def pair_pin(host: str, port: int, pin: str) -> dict:
    import websockets

    uri = f"ws://{host}:{port}"
    print(f"Connecting (plaintext pair) to {uri} ...")
    async with websockets.connect(uri, open_timeout=10) as ws:
        await ws.send(json.dumps({"v": 1, "cmd": "pair", "pin": pin}))
        raw = await asyncio.wait_for(ws.recv(), timeout=10)
        body = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
        print("Response:", json.dumps(body, indent=2))
        if not body.get("ok"):
            raise RuntimeError(body.get("error", "pair failed"))
        return body


def main() -> int:
    p = argparse.ArgumentParser(description="Test PIN pairing like the Android app")
    p.add_argument("--host", default="192.168.1.2", help="PC LAN IP from Pair Mobile")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--pin", required=True, help="6-digit code from Pair Mobile")
    args = p.parse_args()
    pin = "".join(c for c in args.pin if c.isdigit())
    if len(pin) != 6:
        print("PIN must be 6 digits", file=sys.stderr)
        return 1
    try:
        asyncio.run(pair_pin(args.host, args.port, pin))
        print("OK PIN pairing")
        return 0
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
