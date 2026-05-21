#!/usr/bin/env python3
"""Test LuminaSync remote WebSocket API without the mobile app."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.remote.crypto import decrypt_json, encrypt_json  # noqa: E402


def _load_pairing(path: str | None, args: argparse.Namespace) -> tuple[str, int, str]:
    if path:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data["host"], int(data["port"]), data["key"]
    if args.host and args.port and args.key:
        return args.host, int(args.port), args.key
    raise SystemExit("Provide --pairing file.json or --host --port --key")


async def _send_cmd(
    ws,
    key: str,
    cmd: str,
    payload: dict | None = None,
) -> dict:
    msg_id = uuid.uuid4().hex[:8]
    body = {"v": 1, "id": msg_id, "cmd": cmd}
    if payload is not None:
        body["payload"] = payload
    wire = encrypt_json(key, json.dumps(body, separators=(",", ":")))
    await ws.send(wire)
    raw = await ws.recv()
    plain = decrypt_json(key, raw if isinstance(raw, str) else raw.decode("utf-8"))
    return json.loads(plain)


async def run_demo(host: str, port: int, key: str) -> None:
    import websockets

    uri = f"ws://{host}:{port}"
    print(f"Connecting to {uri} ...")
    async with websockets.connect(uri, max_size=16384) as ws:
        pong = await _send_cmd(ws, key, "ping")
        print("ping:", pong)
        state = await _send_cmd(ws, key, "get_state")
        print("state:", json.dumps(state, indent=2))
        sliders = state.get("state", {}).get("sliders", {})
        sliders["vibrance"] = min(100.0, float(sliders.get("vibrance", 50)) + 10)
        updated = await _send_cmd(ws, key, "set_sliders", sliders)
        print("set_sliders:", json.dumps(updated, indent=2))
        await asyncio.sleep(1)
        restored = await _send_cmd(ws, key, "set_sliders", state.get("state", {}).get("sliders", {}))
        print("restored:", json.dumps(restored, indent=2))


async def run_interactive(host: str, port: int, key: str) -> None:
    import websockets

    uri = f"ws://{host}:{port}"
    print(f"Connected to {uri}. Commands: state | observer on|off | set v b c g h | reset | quit")
    async with websockets.connect(uri, max_size=16384) as ws:
        while True:
            line = await asyncio.to_thread(input, "> ")
            parts = line.strip().split()
            if not parts:
                continue
            if parts[0] in ("quit", "exit", "q"):
                break
            if parts[0] == "state":
                print(await _send_cmd(ws, key, "get_state"))
            elif parts[0] == "observer" and len(parts) >= 2:
                en = parts[1].lower() in ("1", "on", "true", "yes")
                print(await _send_cmd(ws, key, "set_observer", {"enabled": en}))
            elif parts[0] == "set" and len(parts) >= 3:
                field = parts[1].lower()
                val = float(parts[2])
                st = await _send_cmd(ws, key, "get_state")
                sliders = dict(st.get("state", {}).get("sliders", {}))
                mapping = {
                    "v": "vibrance",
                    "vibrance": "vibrance",
                    "b": "brightness",
                    "c": "contrast",
                    "g": "gamma",
                    "h": "hue",
                }
                key_name = mapping.get(field)
                if not key_name:
                    print("unknown field")
                    continue
                sliders[key_name] = val
                print(await _send_cmd(ws, key, "set_sliders", sliders))
            elif parts[0] == "reset":
                print(await _send_cmd(ws, key, "reset_profile", {}))
            else:
                print("unknown command")


def main() -> int:
    parser = argparse.ArgumentParser(description="LuminaSync remote WebSocket test client")
    parser.add_argument("--pairing", help="JSON file from QR / Copy JSON")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--key")
    parser.add_argument("--demo", action="store_true", help="Run automated slider demo")
    args = parser.parse_args()

    host, port, key = _load_pairing(args.pairing, args)
    if args.demo:
        asyncio.run(run_demo(host, port, key))
    else:
        asyncio.run(run_interactive(host, port, key))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
