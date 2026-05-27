# VibranceFlow Core

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)

VibranceFlow Core is the Windows desktop app for game-based color profiles and local mobile pairing.

## Release 1.0 scope

- Supported desktop platform: **Windows 11**
- Public build format: **single-file `.exe`**
- Mobile companion for this release: **Android APK** (from `VibranceFlow-mobile`)

## Download and install (Windows)

1. Open the repository **Releases** page.
2. Download the latest `VibranceFlow.exe` artifact.
3. Place it in any folder (for example `C:\Program Files\VibranceFlow\`).
4. Run `VibranceFlow.exe`.

If Windows SmartScreen appears, choose **More info** and run only when the release is from the official repository.

## First run

1. Open VibranceFlow.
2. Add a game executable from the process list or manually from disk.
3. Configure sliders (Vibrance, Brightness, Contrast, Gamma, Hue).
4. Optional: configure per-app audio when a live audio session exists.
5. Open **Pair Mobile** to connect your Android phone over LAN.

## Firewall and LAN pairing

Mobile control uses local WebSocket on port `8765`.

When Windows Firewall prompts:

- allow on **Private networks**
- keep **Public networks** disabled unless you explicitly need it

Pairing options:

- 6-digit pairing code
- QR code (recommended)

All commands are encrypted end-to-end on LAN using Fernet payload encryption.

## Privacy and security

- No cloud account is required.
- No telemetry backend is required for normal use.
- Pairing keys stay local and can be rotated from the Pair Mobile dialog.

## Troubleshooting

- **Mobile cannot connect:** confirm phone and PC are on the same LAN and firewall allows private access.
- **Audio slider is disabled:** the selected app has no active audio session on the PC.
- **Profile not switching:** verify Observer is enabled and the executable is saved in the profile list.

## For developers

Development setup, packaging notes, and contribution rules are documented in [CONTRIBUTING.md](CONTRIBUTING.md) and [packaging/README.md](packaging/README.md).

## License

GPL-3.0 — see [LICENSE](LICENSE).
