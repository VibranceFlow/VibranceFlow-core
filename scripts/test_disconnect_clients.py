#!/usr/bin/env python3
"""Smoke test: RemoteServer.disconnect_all_clients is public and callable."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.remote.server import RemoteServer  # noqa: E402


def main() -> int:
    if not hasattr(RemoteServer, "disconnect_all_clients"):
        print("FAIL: RemoteServer.disconnect_all_clients missing")
        return 1
    if not callable(getattr(RemoteServer, "disconnect_all_clients")):
        print("FAIL: disconnect_all_clients is not callable")
        return 1
    print("OK disconnect_all_clients public API")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
