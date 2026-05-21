#!/usr/bin/env python3
"""LuminaSync — graphical user interface entry point."""

from __future__ import annotations

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

from ui.app_context import LuminaAppContext
from ui.main_window import LuminaSyncWindow


def main() -> int:
    start_hidden = "--tray" in sys.argv or "--minimized" in sys.argv

    try:
        ctx = LuminaAppContext()
    except Exception as e:
        print(f"Failed to start LuminaSync: {e}", file=sys.stderr)
        return 1

    app = LuminaSyncWindow(ctx, start_hidden=start_hidden)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
