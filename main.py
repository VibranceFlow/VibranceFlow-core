#!/usr/bin/env python3
"""VibranceFlow - CLI engine entry point (no GUI)."""

from __future__ import annotations

import atexit
import logging
import signal
import sys

from core.display_manager import WindowsDisplayManager
from core.engine import VibranceFlowEngine
from core.profile_manager import ProfileManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vibranceflow")


def main() -> int:
    profiles = ProfileManager()
    executables = profiles.list_executables()
    if not executables:
        logger.warning(
            "No profiles at %s - copy profiles.json.example and add games.",
            profiles.path,
        )
    else:
        logger.info("Profiles loaded: %s", ", ".join(executables))

    display = WindowsDisplayManager()
    engine = VibranceFlowEngine(display, profiles)

    def _shutdown() -> None:
        if engine.is_running:
            engine.stop()
        display.shutdown()

    atexit.register(_shutdown)

    def _signal_handler(_signum, _frame) -> None:
        logger.info("Shutting down...")
        _shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _signal_handler)

    logger.info("VibranceFlow running. Press Ctrl+C to exit.")
    engine.start()

    import time

    while engine.is_running:
        time.sleep(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
