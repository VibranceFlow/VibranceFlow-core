"""Async WebSocket server (background thread)."""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable
from typing import Any

from core.remote.crypto import decrypt_json, encrypt_json, generate_key
from core.remote.handlers import RemoteCommandHandler
from core.remote.pairing import DEFAULT_PORT, build_pairing_payload, get_lan_ipv4

logger = logging.getLogger(__name__)

MAX_WS_MESSAGE_BYTES = 16384


class RemoteServer:
    def __init__(
        self,
        handler: RemoteCommandHandler,
        *,
        port: int = DEFAULT_PORT,
        on_main_thread: Callable[[Callable[[], Any]], None],
    ) -> None:
        self._handler = handler
        self._port = port
        self._on_main = on_main_thread
        self._key = generate_key()
        self._host = get_lan_ipv4()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server: Any = None
        self._clients: set[Any] = set()
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def pairing_payload(self) -> dict[str, Any]:
        return build_pairing_payload(self._host, self._port, self._key)

    @property
    def port(self) -> int:
        return self._port

    @property
    def host(self) -> str:
        return self._host

    def regenerate_key(self) -> None:
        with self._lock:
            self._key = generate_key()
        self._disconnect_all_clients()

    def start(self) -> None:
        if self.is_running:
            return
        self._host = get_lan_ipv4()
        self._thread = threading.Thread(target=self._run_loop, name="LuminaRemoteWS", daemon=True)
        self._thread.start()
        logger.info("Remote server starting on %s:%s", self._host, self._port)

    def stop(self) -> None:
        if self._loop is None:
            return

        async def _shutdown() -> None:
            for ws in list(self._clients):
                await ws.close()
            self._clients.clear()
            if self._server is not None:
                self._server.close()
                await self._server.wait_closed()

        try:
            asyncio.run_coroutine_threadsafe(_shutdown(), self._loop).result(timeout=5)
        except Exception as e:
            logger.warning("Remote server shutdown: %s", e)
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=3)
        self._thread = None
        self._loop = None
        self._server = None

    def _disconnect_all_clients(self) -> None:
        if self._loop is None:
            return

        async def _close() -> None:
            for ws in list(self._clients):
                await ws.close()
            self._clients.clear()

        try:
            asyncio.run_coroutine_threadsafe(_close(), self._loop).result(timeout=3)
        except Exception:
            pass

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except Exception:
            logger.exception("Remote server loop crashed")
        finally:
            self._loop.close()

    async def _serve(self) -> None:
        import websockets
        from websockets.server import serve

        async def _handler(websocket: Any) -> None:
            self._clients.add(websocket)
            try:
                async for message in websocket:
                    if isinstance(message, bytes):
                        if len(message) > MAX_WS_MESSAGE_BYTES:
                            await websocket.close(1009, "message too large")
                            break
                        text = message.decode("utf-8", errors="strict")
                    else:
                        text = message
                        if len(text.encode("utf-8")) > MAX_WS_MESSAGE_BYTES:
                            await websocket.close(1009, "message too large")
                            break

                    reply = await self._process_message(text)
                    if reply is not None:
                        await websocket.send(reply)
            except Exception:
                logger.debug("client disconnected", exc_info=True)
            finally:
                self._clients.discard(websocket)

        bind_host = self._host if self._host != "127.0.0.1" else "0.0.0.0"
        self._server = await serve(
            _handler,
            bind_host,
            self._port,
            max_size=MAX_WS_MESSAGE_BYTES,
            ping_interval=30,
            ping_timeout=10,
        )
        logger.info("Remote server listening on %s:%s (LAN IP %s)", bind_host, self._port, self._host)
        await self._server.wait_closed()

    async def _process_message(self, wire: str) -> str | None:
        key = self._key
        try:
            plaintext = decrypt_json(key, wire.strip())
        except ValueError:
            logger.warning("Rejected remote frame (decrypt failed)")
            return encrypt_json(key, '{"v":1,"ok":false,"error":"unauthorized"}')

        def _dispatch() -> str:
            return self._handler.handle(plaintext)

        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(None, lambda: self._sync_on_main(_dispatch))
        result = await future
        return encrypt_json(key, result)

    def _sync_on_main(self, fn: Callable[[], str]) -> str:
        box: list[str] = []
        done = threading.Event()

        def _run() -> None:
            try:
                box.append(fn())
            except Exception as e:
                logger.exception("main thread remote dispatch failed")
                box.append('{"v":1,"ok":false,"error":"internal error"}')
            finally:
                done.set()

        self._on_main(_run)
        done.wait(timeout=10.0)
        return box[0] if box else '{"v":1,"ok":false,"error":"timeout"}'
