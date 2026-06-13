#!/usr/bin/env python3
"""Smoke test: remote server restart cycle (stop then start again)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.remote.health import is_port_in_use, probe_port_listening  # noqa: E402
from core.remote.pairing import DEFAULT_PORT  # noqa: E402
from scripts.test_remote_boot import run_boot_test  # noqa: E402


def main() -> int:
    try:
        run_boot_test()
        if is_port_in_use(DEFAULT_PORT):
            print("FAIL: port still in use immediately after stop")
            return 1
        run_boot_test()
        print("OK remote restart cycle (boot x2)")
        return 0
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
