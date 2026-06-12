#!/usr/bin/env python3
"""Assert LAN protocol v1 constants (CI guard — must match mobile INTEGRATION.md)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.remote.pairing import DEFAULT_PORT, PROTOCOL_VERSION  # noqa: E402

EXPECTED_VERSION = 1
EXPECTED_PORT = 8765


def main() -> int:
    ok = True
    if PROTOCOL_VERSION != EXPECTED_VERSION:
        print(f"FAIL: PROTOCOL_VERSION={PROTOCOL_VERSION}, expected {EXPECTED_VERSION}")
        ok = False
    if DEFAULT_PORT != EXPECTED_PORT:
        print(f"FAIL: DEFAULT_PORT={DEFAULT_PORT}, expected {EXPECTED_PORT}")
        ok = False
    if ok:
        print(f"OK protocol v{EXPECTED_VERSION} port {EXPECTED_PORT}")
        return 0
    print("Bump INTEGRATION.md and VibranceFlow-mobile together when changing these.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
