"""Thread-safe dispatch to the Tk main thread."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from typing import Any


class MainThreadBridge:
    def __init__(self, schedule: Callable[[Callable[[], Any]], None]) -> None:
        self._schedule = schedule
        self._queue: queue.Queue[tuple[Callable[[], Any], threading.Event, list[Any]]] = (
            queue.Queue()
        )

    def call(self, fn: Callable[[], Any], *, timeout: float = 5.0) -> Any:
        """Run fn on the main thread and return its result (blocks caller thread)."""
        done = threading.Event()
        box: list[Any] = []

        def _wrapper() -> None:
            try:
                box.append(fn())
            except Exception as e:
                box.append(e)
            finally:
                done.set()

        self._schedule(_wrapper)
        if not done.wait(timeout):
            raise TimeoutError("main thread handler timed out")
        result = box[0] if box else None
        if isinstance(result, Exception):
            raise result
        return result

    def fire_and_forget(self, fn: Callable[[], None]) -> None:
        self._schedule(fn)
