#!/usr/bin/env python3
"""VibranceFlow — graphical user interface entry point."""

from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path


def _configure_logging() -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    log_path: Path | None = None
    if os.environ.get("VIBRANCEFLOW_LOG"):
        log_path = Path(os.environ["VIBRANCEFLOW_LOG"])
    elif getattr(sys, "frozen", False):
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            if appdata:
                log_path = Path(appdata) / "VibranceFlow" / "app.log"
        elif sys.platform == "darwin":
            log_path = Path.home() / "Library" / "Logs" / "VibranceFlow" / "app.log"
        else:
            state = os.environ.get("XDG_STATE_HOME")
            base = Path(state) if state else Path.home() / ".local" / "state"
            log_path = base / "vibranceflow" / "app.log"
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
        force=True,
    )


_configure_logging()

from core.single_instance import acquire_single_instance, show_already_running_message
from ui.app_context import VibranceFlowAppContext
from ui.main_window import VibranceFlowWindow

logger = logging.getLogger(__name__)


def _report_fatal_error(title: str, message: str) -> None:
    logger.exception("%s: %s", title, message)
    if getattr(sys, "frozen", False):
        try:
            import tkinter.messagebox as messagebox

            messagebox.showerror(title, message)
        except Exception:
            pass


def main() -> int:
    if not acquire_single_instance():
        show_already_running_message()
        return 1

    start_hidden = "--tray" in sys.argv or "--minimized" in sys.argv

    try:
        ctx = VibranceFlowAppContext()
    except Exception as e:
        _report_fatal_error("VibranceFlow startup failed", str(e))
        print(f"Failed to start VibranceFlow: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1

    try:
        app = VibranceFlowWindow(ctx, start_hidden=start_hidden)
    except Exception as e:
        ctx.shutdown()
        _report_fatal_error("VibranceFlow UI failed", str(e))
        print(f"Failed to create VibranceFlow window: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1

    ctx.attach_ui_scheduler(lambda fn, delay=0: app.after(delay, fn))
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
