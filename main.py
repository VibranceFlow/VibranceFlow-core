#!/usr/bin/env python3
"""LuminaSync — entry point do motor (sem GUI)."""

from __future__ import annotations

import atexit
import logging
import signal
import sys

from core.display_manager import WindowsDisplayManager
from core.engine import LuminaEngine
from core.profile_manager import ProfileManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("lumina_sync")


def main() -> int:
    profiles = ProfileManager()
    executables = profiles.list_executables()
    if not executables:
        logger.warning(
            "Nenhum perfil em %s — copie profiles.json.example e configure jogos.",
            profiles.path,
        )
    else:
        logger.info("Perfis carregados: %s", ", ".join(executables))

    display = WindowsDisplayManager()
    engine = LuminaEngine(display, profiles)

    def _shutdown() -> None:
        if engine.is_running:
            engine.stop()
        display.shutdown()

    atexit.register(_shutdown)

    def _signal_handler(_signum, _frame) -> None:
        logger.info("Encerrando...")
        _shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _signal_handler)

    logger.info("LuminaSync ativo. Ctrl+C para sair.")
    engine.start()

    import time

    while engine.is_running:
        time.sleep(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
