"""Windows Firewall helper for the LAN WebSocket server."""

from __future__ import annotations

import logging
import subprocess
import sys

from core.remote.pairing import DEFAULT_PORT

logger = logging.getLogger(__name__)

_RULES_ADDED: set[int] = set()
_APP_RULE_ADDED = False


def _rule_name(port: int) -> str:
    return f"VibranceFlow Remote TCP {port}"


def _rule_exists(port: int) -> bool:
    name = _rule_name(port)
    try:
        r = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={name}"],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        logger.debug("firewall show rule failed: %s", e)
        return False
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode == 0 and "No rules match" not in out and name in out


def ensure_firewall_rule(port: int = DEFAULT_PORT) -> str | None:
    """
    Allow inbound TCP on private networks. May trigger Windows Firewall / UAC prompt.
    Returns a short warning for the UI, or None on success / non-Windows.
    """
    if sys.platform != "win32":
        return None
    if port in _RULES_ADDED or _rule_exists(port):
        _RULES_ADDED.add(port)
        return None

    name = _rule_name(port)
    exe = sys.executable
    args_port = [
        "netsh",
        "advfirewall",
        "firewall",
        "add",
        "rule",
        f"name={name}",
        "dir=in",
        "action=allow",
        "protocol=TCP",
        f"localport={port}",
        "profile=any",
    ]
    try:
        r = subprocess.run(
            args_port,
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        logger.warning("firewall add rule failed: %s", e)
        return (
            "Could not add a firewall rule automatically. "
            f"Allow VibranceFlow (TCP {port}) on private networks in Windows Firewall."
        )

    if r.returncode != 0:
        err = (r.stderr or r.stdout or "").strip()
        logger.warning("netsh firewall add failed (%s): %s", r.returncode, err)
        if "access is denied" in err.lower() or "elevação" in err.lower() or "elevation" in err.lower():
            return (
                "Firewall change needs administrator approval. "
                f"Allow inbound TCP port {port} for VibranceFlow on private networks."
            )
        return (
            f"Firewall rule was not added (TCP {port}). "
            "Allow VibranceFlow on private networks if the phone cannot connect."
        )

    _RULES_ADDED.add(port)
    logger.info("Firewall rule added: %s (TCP %s)", name, port)
    _try_add_app_rule(exe)
    return None


def _try_add_app_rule(exe: str) -> None:
    global _APP_RULE_ADDED
    if _APP_RULE_ADDED or sys.platform != "win32":
        return
    app_name = "VibranceFlow Python"
    try:
        r = subprocess.run(
            [
                "netsh",
                "advfirewall",
                "firewall",
                "add",
                "rule",
                f"name={app_name}",
                "dir=in",
                "action=allow",
                "program=" + exe,
                "enable=yes",
                "profile=any",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        if r.returncode == 0:
            _APP_RULE_ADDED = True
            logger.info("Firewall app rule added for %s", exe)
    except (OSError, subprocess.TimeoutExpired):
        pass
