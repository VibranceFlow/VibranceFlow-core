# Error handling - VibranceFlow Core

How the desktop app surfaces failures for LAN remote, profiles, and display.

## Remote WebSocket (v1)

| Situation | Wire response | Logs | UI |
| --------- | ------------- | ---- | -- |
| Decrypt fail (wrong key) | Encrypted `ok:false`, `error:"unauthorized"` | WARNING with frame length | Mobile must re-pair |
| Invalid command JSON | `ok:false`, `error` + optional `error_code` | - | - |
| Handler exception | `ok:false`, `error:"internal error"`, `error_code:"internal_error"` | `logger.exception` | - |
| Profile save failed | `ok:false`, `error:"profile save failed"`, `error_code:"profile_save_failed"` | ERROR | - |
| Main-thread dispatch timeout | `ok:false`, `error:"timeout"` | - | Mobile command timeout |
| Port stop | Encrypted `event:"port_closed"` then close | INFO | Mobile waiting + reconnect |
| PIN wrong / expired | Plaintext `error:"invalid or expired code"` | WARNING with peer IP | Pair Mobile dialog |
| PIN lockout | Plaintext `error:"too_many_attempts"` | WARNING lockout + peer | Mobile: wait ~60s |

Stable `error_code` values (when present): `too_large`, `invalid_json`, `unknown_cmd`, `bad_version`, `profile_save_failed`, `internal_error`, plus `ProtocolError.code` from [`core/remote/protocol.py`](../core/remote/protocol.py).

## `get_state.remote` (optional diagnostics)

```json
"remote": {
  "listening": true,
  "client_count": 1,
  "last_error": null,
  "nvapi_available": true
}
```

Mobile may use this for troubleshooting; fields are optional in v1.

## Desktop UI

- **Keep remote port open** failure: setting rolled back + messagebox; status bar shows `remote error (<detail>)` when `remote_last_error` is set.
- **Pair Mobile / New code**: messagebox on start or key rotation failure.
- **Auto-start remote** on launch: failure stored in `remote_last_error` (visible in status bar when keep-port is on).

## Display / profiles

- **NVAPI unavailable**: GDI-only; vibrance/hue skipped with debug log.
- **`apply_profile`**: each step (gamma, vibrance, hue) isolated - one failure does not block the others; errors logged at ERROR.
- **`ProfileManager.save()`**: raises `ProfileSaveError` on disk/permission errors (not silent).

## Public API fix

`RemoteServer.disconnect_all_clients()` disconnects phones without stopping the server (used when re-opening Pair Mobile with an active client).

Tests: `scripts/test_disconnect_clients.py`, `scripts/test_remote_boot.py`, `scripts/verify_protocol_v1.py`.

See also: [`docs/REMOTE_PROTOCOL.md`](REMOTE_PROTOCOL.md), mobile [`INTEGRATION.md`](https://github.com/VibranceFlow/VibranceFlow-mobile/blob/main/docs/INTEGRATION.md).
