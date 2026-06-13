# Remote protocol (contributor summary)

This document summarizes the LAN remote stack in **VibranceFlow-core**. The **canonical wire contract** (JSON schemas, field ranges, versioning rules) lives in the mobile repo:

**[VibranceFlow-mobile/docs/INTEGRATION.md](https://github.com/VibranceFlow/VibranceFlow-mobile/blob/main/docs/INTEGRATION.md)**

When changing the protocol, update **both** repositories and bump wire `"v"` together.

## Stack (v1)

| Item | Value |
| ---- | ----- |
| Port | `8765` (`core/remote/pairing.py`) |
| Bind | `0.0.0.0` (phones connect via advertised LAN IP) |
| Transport | `ws://` (no TLS on LAN v1) |
| Session crypto | Fernet (`core/remote/crypto.py`) |
| Mobile mirror | `VibranceFlow-mobile/src/lib/fernetWire.ts` |

Wire encoding: JSON → Fernet → inner base64url (with `=` padding) → outer base64url.

## Pairing

1. **PIN (primary):** phone sends plaintext `{"v":1,"cmd":"pair","pin":"######"}` → PC responds once with plaintext `{"ok":true,"host","port","key"}`.
2. **QR (alternative):** JSON `{v, host, port, key}` scanned or pasted - no PIN step.

After pairing, all frames are Fernet-encrypted. Re-pair after **New code** on PC or LAN IP change.

Implementation: `core/remote/pin.py`, `core/remote/pairing.py`, `ui/pairing_dialog.py`.

## Commands (v1)

`ping`, `get_state`, `set_sliders`, `set_audio`, `set_observer`, `reset_profile`

Handlers: `core/remote/handlers.py`. Server: `core/remote/server.py`.

## Tests

```powershell
poetry run python scripts/verify_protocol_v1.py
poetry run python scripts/test_remote_boot.py
poetry run python scripts/test_prepare_pairing.py
```

Cross-repo Fernet: `scripts/test_fernet_cmds.py` with mobile `scripts/test-fernet-cmds-export.ts`.

## Security notes

See [SECURITY.md](../SECURITY.md) for threat model, pairing cleartext window, and firewall behavior.

Operational error matrix: [ERROR_HANDLING.md](ERROR_HANDLING.md).
