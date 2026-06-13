#!/usr/bin/env python3
"""LAN remote diagnostics - run while VibranceFlow GUI is open (Pair Mobile)."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.remote.firewall import is_firewall_configured  # noqa: E402
from core.remote.pairing import DEFAULT_PORT, get_lan_ipv4, get_lan_ipv4_candidates  # noqa: E402

RULE_NAME = f"VibranceFlow Remote TCP {DEFAULT_PORT}"


def _port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _listening_process(port: int) -> str:
    try:
        r = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "(netstat unavailable)"
    for line in (r.stdout or "").splitlines():
        if f":{port}" in line and "LISTENING" in line:
            return line.strip()
    return "(nothing listening)"


def _network_profiles() -> list[str]:
    if sys.platform != "win32":
        return []
    try:
        r = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-NetConnectionProfile | Select-Object InterfaceAlias,NetworkCategory | ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if r.returncode != 0:
            return [r.stderr.strip() or "Get-NetConnectionProfile failed"]
        data = json.loads(r.stdout.strip() or "[]")
        if isinstance(data, dict):
            data = [data]
        return [f"{d.get('InterfaceAlias')}: {d.get('NetworkCategory')}" for d in data]
    except Exception as e:
        return [str(e)]


def main() -> int:
    port = DEFAULT_PORT
    lan = get_lan_ipv4()
    candidates = get_lan_ipv4_candidates()
    fw_ok = is_firewall_configured(port)
    loop_ok = _port_open("127.0.0.1", port)
    lan_ok = _port_open(lan, port) if lan and not lan.startswith("127.") else False

    print("=== VibranceFlow LAN remote diagnostics ===\n")
    print(f"Port: {port}")
    print(f"Advertised LAN IP: {lan}")
    if candidates:
        print(f"All LAN IPv4 candidates: {', '.join(candidates)}")
    print(f"Firewall rule configured: {'yes' if fw_ok else 'no'} ({RULE_NAME})")
    print(f"TCP {port} on 127.0.0.1: {'OPEN' if loop_ok else 'CLOSED'}")
    if not lan.startswith("127."):
        print(f"TCP {port} on {lan}: {'OPEN' if lan_ok else 'CLOSED'}")
    print(f"netstat: {_listening_process(port)}")
    print("\nNetwork profiles:")
    for line in _network_profiles():
        print(f"  - {line}")

    print("\n--- Interpretation ---")
    if not loop_ok:
        print(
            "FAIL: Nothing is listening on port 8765.\n"
            "  - Open VibranceFlow, click Pair Mobile (or enable Keep remote port open).\n"
            "  - Leave the app running while testing the phone."
        )
        return 1

    if lan.startswith("127."):
        print(
            "WARN: PC could not detect a LAN IPv4. Phone cannot use 127.0.0.1.\n"
            "  - Connect PC via Wi-Fi or Ethernet with a 192.168.x.x address."
        )
        return 1

    if not fw_ok:
        print(
            "WARN: Firewall rule missing. In Pair Mobile click Allow in Firewall.\n"
            "  - Phone may not connect even if the server is running."
        )

    if loop_ok and not lan_ok:
        print(
            "WARN: Loopback works but LAN IP test failed (unusual).\n"
            "  - Check Windows Firewall profile is Private on the active adapter."
        )

    if loop_ok:
        print(
            "OK: Server reachable on this PC.\n"
            f"  - On the phone (Wi-Fi only, 4G OFF): IP = {lan}, port = {port}\n"
            "  - If phone still fails: router AP/client isolation, or phone on a different subnet.\n"
            "  - Test PIN before QR. Use Copy JSON + ws_remote_client.py on PC to verify Fernet."
        )

    print("\nPhone checklist:")
    print("  1. Mobile data OFF (Wi‑Fi only)")
    print(f"  2. Phone Wi‑Fi IP should be 192.168.1.x (same subnet as {lan})")
    print("  3. Forget pairing in app, enter fresh 6-digit code from Pair Mobile")
    print("  4. Disable VPN on phone and PC")
    print("\nWhile testing from the phone, watch the PC console for:")
    print("  WS handshake from ('192.168.1.xx', ...)  -> phone reached the PC")
    print("  connection rejected (400 Bad Request)     -> bad WS handshake (update core)")
    print("  (nothing new)                               -> phone blocked before TCP (router isolation)")
    return 0 if loop_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
