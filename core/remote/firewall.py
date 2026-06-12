"""Windows Firewall helper for the LAN WebSocket server."""

from __future__ import annotations

import ctypes
import logging
import subprocess
import sys
import time

from core.remote.pairing import DEFAULT_PORT

logger = logging.getLogger(__name__)

_RULES_ADDED: set[int] = set()
_APP_RULE_ADDED = False

# ShellExecuteW return codes <= 32 indicate failure (incl. user cancelled UAC).
_SHELL_EXECUTE_SUCCESS_MIN = 32


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


def is_firewall_configured(port: int = DEFAULT_PORT) -> bool:
    """True when an inbound rule for this port already exists (or was added this session)."""
    if port in _RULES_ADDED:
        return True
    if sys.platform != "win32":
        return True
    if _rule_exists(port):
        _RULES_ADDED.add(port)
        return True
    return False


def request_elevated_firewall_rule(port: int = DEFAULT_PORT) -> tuple[bool, str | None]:
    """
    Show the Windows UAC prompt once to add the inbound TCP rule.

    Returns (uac_launched, error_message). The rule may appear a moment after approval.
    """
    if sys.platform != "win32":
        return False, _manual_firewall_hint(port)
    if is_firewall_configured(port):
        return True, None

    name = _rule_name(port)
    params = (
        f"advfirewall firewall add rule "
        f'name="{name}" dir=in action=allow protocol=TCP localport={port} profile=private'
    )
    try:
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", "netsh", params, None, 0)
    except OSError as e:
        logger.warning("elevated firewall ShellExecute failed: %s", e)
        return False, "Could not open the administrator prompt."

    if ret <= _SHELL_EXECUTE_SUCCESS_MIN:
        logger.info("elevated firewall UAC not launched (code %s)", ret)
        return False, "Administrator approval was cancelled or denied."

    for _ in range(24):
        time.sleep(0.25)
        if _rule_exists(port):
            _RULES_ADDED.add(port)
            logger.info("Firewall rule added via UAC: %s (TCP %s)", name, port)
            return True, None

    return True, None


def _manual_firewall_hint(port: int) -> str | None:
    if sys.platform.startswith("linux"):
        return (
            f"Allow inbound TCP {port} in your firewall (e.g. ufw allow {port}/tcp) "
            "if the phone cannot connect on LAN."
        )
    if sys.platform == "darwin":
        return (
            f"Allow VibranceFlow incoming connections in macOS Firewall "
            f"(TCP {port}) if the phone cannot connect on LAN."
        )
    return None


def ensure_firewall_rule(port: int = DEFAULT_PORT) -> str | None:
    """
    Try to add an inbound TCP rule without elevation.

    Returns a short warning for the UI, or None on success. Never blocks server bind.
    Use request_elevated_firewall_rule() when the user opts in (UAC once).
    """
    if sys.platform != "win32":
        return _manual_firewall_hint(port)
    if is_firewall_configured(port):
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
        "profile=private",
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
                f"Firewall needs administrator approval for TCP {port}. "
                'Click "Allow in Firewall" below and approve the UAC prompt.'
            )
        return (
            f"Firewall rule was not added (TCP {port}). "
            'Use "Allow in Firewall" below or allow VibranceFlow on private networks manually.'
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
