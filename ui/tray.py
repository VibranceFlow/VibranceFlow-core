"""System tray — pystray."""

from __future__ import annotations

import threading
from typing import Callable

from PIL import Image, ImageDraw


def _default_icon_image() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (10, 10, 15, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse((10, 10, 54, 54), fill=(0, 229, 192, 255))
    draw.ellipse((26, 26, 38, 38), fill=(139, 92, 246, 255))
    return img


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
            pystray.MenuItem("Open LuminaSync", self._handle_show, default=True),
            pystray.MenuItem("Quit", self._handle_quit),
        )
        self._icon = pystray.Icon("LuminaSync", _default_icon_image(), "LuminaSync", menu)

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
