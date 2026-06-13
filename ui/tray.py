"""System tray - pystray."""

from __future__ import annotations

import threading
from typing import Callable

from ui.brand_assets import load_tray_image


class TrayController:
    def __init__(
        self,
        on_show: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._on_show = on_show
        self._on_quit = on_quit
        self._icon = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        import pystray

        menu = pystray.Menu(
            pystray.MenuItem("Open VibranceFlow", self._handle_show, default=True),
            pystray.MenuItem("Quit", self._handle_quit),
        )
        self._icon = pystray.Icon("VibranceFlow", load_tray_image(), "VibranceFlow", menu)

        def _run() -> None:
            assert self._icon is not None
            self._icon.run()

        self._thread = threading.Thread(target=_run, name="TrayIcon", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._icon is not None:
            self._icon.stop()
            self._icon = None

    def notify(self, title: str, message: str) -> None:
        if self._icon is not None:
            try:
                self._icon.notify(message, title)
            except Exception:
                pass

    def _handle_show(self, _icon, _item) -> None:
        self._on_show()

    def _handle_quit(self, _icon, _item) -> None:
        self._on_quit()
