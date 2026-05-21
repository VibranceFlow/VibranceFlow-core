"""UI utilities."""

from __future__ import annotations

from typing import Callable


class Debouncer:
    def __init__(self, widget, delay_ms: int, callback: Callable[[], None]) -> None:
        self._widget = widget
        self._delay = delay_ms
        self._callback = callback
        self._job: str | None = None

    def trigger(self) -> None:
        if self._job is not None:
            self._widget.after_cancel(self._job)
        self._job = self._widget.after(self._delay, self._fire)

    def _fire(self) -> None:
        self._job = None
        self._callback()

    def cancel(self) -> None:
        if self._job is not None:
            self._widget.after_cancel(self._job)
            self._job = None
