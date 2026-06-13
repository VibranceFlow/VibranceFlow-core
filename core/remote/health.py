"""Remote server health checks - portable across OS."""

from __future__ import annotations

import socket


class RemoteStartError(RuntimeError):
    """Raised when the LAN WebSocket server cannot start or listen."""


class PortInUseError(RemoteStartError):
    """Raised when the remote port is held by another process."""


def verify_remote_dependencies() -> str | None:
    """Return an error message if remote stack imports are missing."""
    try:
        import websockets  # noqa: F401
        from websockets.server import serve  # noqa: F401
    except ImportError as e:
        return f"websockets package unavailable: {e}"
    try:
        from cryptography.fernet import Fernet  # noqa: F401
    except ImportError as e:
        return f"cryptography package unavailable: {e}"
    return None


def is_port_in_use(port: int, host: str = "0.0.0.0") -> bool:
    """Return True if host:port cannot be bound (another listener owns it)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        return False
    except OSError:
        return True
    finally:
        sock.close()


def probe_port_listening(host: str, port: int, *, timeout: float = 0.5) -> bool:
    """Return True if a TCP connection to host:port succeeds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def format_start_error(exc: BaseException) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    lower = text.lower()
    if "address already in use" in lower or "only one usage" in lower or "eaddrinuse" in lower:
        return (
            "Port 8765 is already in use. Close the other VibranceFlow or any app using this port."
        )
    if "permission denied" in lower or "access is denied" in lower:
        return f"Permission denied binding the remote port. ({text})"
    if "modulenotfound" in lower or "no module named" in lower:
        return f"Missing dependency in packaged build: {text}"
    return text
