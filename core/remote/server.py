"""Async WebSocket server (background thread)."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from collections.abc import Callable
from typing import Any

import websockets
from websockets.asyncio.server import serve

from core.remote.crypto import decrypt_json, encrypt_json, generate_key
from core.remote.health import format_start_error
from core.remote.handlers import RemoteCommandHandler
from core.remote.pairing import DEFAULT_PORT, build_pairing_payload, get_lan_ipv4
from core.remote.pin import PairingPinManager, build_pair_response, parse_pair_request

logger = logging.getLogger(__name__)

MAX_WS_MESSAGE_BYTES = 16384


class RemoteServer:
    def __init__(
        self,
        handler: RemoteCommandHandler,
        *,
        port: int = DEFAULT_PORT,
        on_main_thread: Callable[[Callable[[], Any]], None],
        on_paired: Callable[[], None] | None = None,
    ) -> None:
        self._handler = handler
        self._port = port
        self._on_main = on_main_thread
        self._on_paired = on_paired
        self._key = generate_key()
        self._host = get_lan_ipv4()
        self._pin = PairingPinManager()
        self._pin.regenerate()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server: Any = None
        self._clients: set[Any] = set()
        self._lock = threading.Lock()
        self._listening = threading.Event()
        self._last_start_error: str | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def is_listening(self) -> bool:
        return self.is_running and self._listening.is_set()

    @property
    def last_start_error(self) -> str | None:
        return self._last_start_error

    @property
    def pairing_payload(self) -> dict[str, Any]:
        return build_pairing_payload(self._host, self._port, self._key)

    @property
    def port(self) -> int:
        return self._port

    @property
    def host(self) -> str:
        return self._host

    @property
    def pairing_pin(self) -> str:
        return self._pin.code

    @property
    def client_count(self) -> int:
        return len(self._clients)

    def refresh_pairing_pin(self) -> str:
        with self._lock:
            if not self._pin.is_active():
                return self._pin.regenerate()
            return self._pin.code

    def regenerate_key(self) -> None:
        with self._lock:
            self._key = generate_key()
            self._pin.regenerate()
        logger.info("Pairing key rotated — connected phones must re-pair")
        self._disconnect_all_clients()

    def start(self) -> None:
        if self.is_running:
            if self.is_listening:
                return
            self.stop()
        self._last_start_error = None
        self._listening.clear()
        self._host = get_lan_ipv4()
        self._thread = threading.Thread(target=self._run_loop, name="VibranceFlowRemoteWS", daemon=True)
        self._thread.start()
        logger.info("Remote server starting on %s:%s", self._host, self._port)

    def restart(self) -> None:
        self.stop()
        self._clear_thread_refs()
        self.start()

    def wait_until_ready(self, timeout: float = 3.0) -> bool:
        if self._listening.wait(timeout):
            return True
        if not self.is_running and self._last_start_error is None:
            self._last_start_error = "Remote server thread exited before listening."
        return False

    def stop(self) -> None:
        if self._thread is None:
            return

        if self._loop is not None:
            async def _shutdown() -> None:
                notice = encrypt_json(
                    self._key,
                    '{"v":1,"ok":false,"error":"port_closed","event":"port_closed"}',
                )
                for ws in list(self._clients):
                    try:
                        await ws.send(notice)
                    except Exception:
                        pass
                    try:
                        await ws.close()
                    except Exception:
                        pass
                self._clients.clear()
                if self._server is not None:
                    self._server.close()
                    await self._server.wait_closed()

            try:
                asyncio.run_coroutine_threadsafe(_shutdown(), self._loop).result(timeout=8)
            except Exception as e:
                logger.warning("Remote server shutdown: %s", e)

        if self._thread is not None:
            self._thread.join(timeout=8)
        self._clear_thread_refs()

    def _clear_thread_refs(self) -> None:
        self._thread = None
        self._loop = None
        self._server = None
        self._listening.clear()

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
        except RuntimeError as e:
            if "Event loop stopped" not in str(e):
                self._last_start_error = format_start_error(e)
                logger.exception("Remote server loop crashed")
        except Exception as e:
            self._last_start_error = format_start_error(e)
            logger.exception("Remote server loop crashed")
        finally:
            self._listening.clear()
            try:
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            except Exception:
                pass
            self._loop.close()
            logger.info("Remote server stopped")

    async def _serve(self) -> None:
        async def _process_request(connection: Any, request: Any) -> None:
            peer = getattr(connection, "remote_address", None)
            logger.info(
                "WS handshake from %s: %s (Origin=%s)",
                peer,
                getattr(request, "path", "?"),
                request.headers.get("Origin", "-") if hasattr(request, "headers") else "-",
            )
            return None

        async def _handler(websocket: Any) -> None:
            peer = getattr(websocket, "remote_address", None)
            logger.info("Remote client connected from %s", peer)
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

        bind_host = "0.0.0.0"
        self._server = await serve(
            _handler,
            bind_host,
            self._port,
            max_size=MAX_WS_MESSAGE_BYTES,
            ping_interval=30,
            ping_timeout=10,
            origins=None,
            compression=None,
            process_request=_process_request,
        )
        logger.info(
            "Remote server listening on %s:%s (LAN IP %s)",
            bind_host,
            self._port,
            self._host,
        )
        self._listening.set()
        await self._server.wait_closed()

    def _try_pair_with_pin(self, wire: str) -> str | None:
        req = parse_pair_request(wire)
        if req is None:
            return None
        pin = str(req.get("pin", ""))
        with self._lock:
            if not self._pin.verify(pin):
                return build_pair_response(ok=False, error="invalid or expired code")
            key = self._key
            host = self._host
            port = self._port
            self._pin.consume()
        if self._on_paired is not None:
            self._on_paired()
        return build_pair_response(ok=True, host=host, port=port, key=key)

    async def _process_message(self, wire: str) -> str | None:
        text = wire.strip()
        pair_reply = self._try_pair_with_pin(text)
        if pair_reply is not None:
            return pair_reply

        key = self._key
        try:
            plaintext = decrypt_json(key, text)
        except ValueError:
            logger.warning(
                "Rejected remote frame (decrypt failed, len=%s) — phone key may be stale after New code",
                len(text),
            )
            return encrypt_json(key, '{"v":1,"ok":false,"error":"unauthorized"}')

        try:
            cmd_hint = json.loads(plaintext).get("cmd", "?")
        except Exception:
            cmd_hint = "?"
        logger.debug("Remote frame ok cmd=%s", cmd_hint)
        if self._on_paired is not None:
            self._on_paired()

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
