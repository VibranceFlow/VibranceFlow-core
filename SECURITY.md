# Security — VibranceFlow Core

VibranceFlow Core is a **local Windows desktop app** with optional **LAN mobile control**. It does not use accounts, cloud backends, or analytics.

## Threat model (v1)

| Threat | Mitigation |
| ------ | ---------- |
| Another device on the same Wi‑Fi reads or forges slider commands | Every WebSocket frame after pairing is **Fernet-encrypted** with a per-session key |
| Brute-force pairing PIN | 6-digit PIN, TTL ~15 minutes, attempt limit with lockout; `compare_digest` for PIN check |
| Oversized or malformed remote commands | Command whitelist, JSON size limits, WebSocket frame limits, rate limiting on server |
| Inbound LAN traffic blocked by Windows Firewall | Optional one-time UAC prompt adds TCP **8765** on **private** profile only |
| Data sent to VibranceFlow servers | **None** — no internet API calls in normal runtime (LAN only) |

This is **local zero-trust**: the LAN is untrusted; only holders of the pairing key can issue valid commands after pairing completes.

## Pairing v1

The primary method is **IP + 6-digit PIN** (works without a camera on the phone). **QR** is an equivalent alternative that delivers `host`, `port`, and `key` directly.

During the pairing window, the PIN exchange and QR JSON are sent in **plaintext** over `ws://`. Anyone on the same LAN who observes traffic during that window can obtain the Fernet key and control the PC until the key is rotated (**New code** in Pair Mobile).

After pairing, all commands use Fernet payload encryption. Transport is **not** TLS (`ws://` on LAN v1).

## Data inventory

| Data | Stored? | Where | Purpose |
| ---- | ------- | ----- | ------- |
| Fernet `key` (session) | Yes (runtime) | In-memory on PC; shown in Pair Mobile UI | Encrypt/decrypt remote commands |
| Color profiles | Yes | `%APPDATA%\VibranceFlow\profiles.json` | Per-game display settings |
| User account / email | No | — | — |
| Crash / analytics telemetry | No | — | Not included in v1 |

Logs (`%APPDATA%\VibranceFlow\app.log` in frozen builds) may include LAN peer IPs and executable names for troubleshooting. PIN and Fernet keys are **not** logged.

## Out of scope for v1

- TLS on LAN (confidentiality is in Fernet payloads, not transport)
- Cloud relay or remote access over the internet
- Post-pairing per-device session tokens (possession of the Fernet key is sufficient)

## Wire protocol (contributors)

Summary: [`docs/REMOTE_PROTOCOL.md`](docs/REMOTE_PROTOCOL.md). Full JSON contract (canonical): [VibranceFlow-mobile `docs/INTEGRATION.md`](https://github.com/VibranceFlow/VibranceFlow-mobile/blob/main/docs/INTEGRATION.md).

## Reporting issues

Open a GitHub issue on [VibranceFlow-core](https://github.com/VibranceFlow/VibranceFlow-core) with steps to reproduce.

**Do not** paste real pairing `key` values, PIN codes, or `pairing.json` contents in public issues.

For release integrity and antivirus false positives, see [README — Security](README.md) and [docs/FALSE_POSITIVE_RUNBOOK.md](docs/FALSE_POSITIVE_RUNBOOK.md).
