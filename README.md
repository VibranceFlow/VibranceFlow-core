# VibranceFlow Core

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Build Windows EXE](https://github.com/VibranceFlow/VibranceFlow-core/actions/workflows/build-windows.yml/badge.svg)](https://github.com/VibranceFlow/VibranceFlow-core/actions/workflows/build-windows.yml)

VibranceFlow Core is the Windows desktop app for game-based color profiles and local mobile pairing.

## Release 1.0 scope

- Supported desktop platform: **Windows 11**
- Public build format: **single-file `.exe`**
- Mobile companion for this release: **Android APK** (from `VibranceFlow-mobile`)

## Download and install (Windows)

Official downloads live on GitHub Releases:

| Build | Releases page |
| --- | --- |
| **Windows** (`VibranceFlow.exe`) | [github.com/VibranceFlow/VibranceFlow-core/releases](https://github.com/VibranceFlow/VibranceFlow-core/releases) |
| **Android APK** (`vibranceflow-release.apk`) | [github.com/VibranceFlow/VibranceFlow-mobile/releases](https://github.com/VibranceFlow/VibranceFlow-mobile/releases) |

Steps on Windows:

1. Open **[VibranceFlow Core Releases](https://github.com/VibranceFlow/VibranceFlow-core/releases)**.
2. Download the latest `VibranceFlow.exe` (and optionally `VibranceFlow.exe.sha256`) from that release.
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

## 🛡️ Security, False Positives & Transparency

VibranceFlow Core is packaged with **Nuitka** (Python to C) as a standalone Windows executable to avoid runtime extraction into temporary folders and to deliver a simple user install flow.  
At runtime, the app must call native Windows APIs (**Win32/NVAPI**) to apply display settings and profile switching.

Because the executable is currently distributed **without a paid EV/OV code-signing certificate**, heuristic and ML-based engines (including SmartScreen and some antivirus models) may classify it as unknown or suspicious by default, even when no malicious behavior exists.

This project follows a strict transparency model:

- 100% open-source codebase
- LAN-only communication model
- encrypted local transport (WebSocket + payload encryption)
- zero analytics and zero telemetry

Transparency — VirusTotal reports (for binaries built from CI for the releases above):

- **Windows** (`VibranceFlow.exe`): [VirusTotal](https://www.virustotal.com/gui/file/9ad23e5a5d2555c60e3d8461a95c34fe02b8760b6d3d9fd60fb354bea3d7f301)
- **Android** (`vibranceflow-release.apk`): [VirusTotal](https://www.virustotal.com/gui/file/8418c3cde2d31a0a63a6c3e96488e57ee47f89e2833051e336440745f2c2bd49)

Before trusting any downloaded executable, always verify integrity:

1. Download `VibranceFlow.exe` and `VibranceFlow.exe.sha256` from the same release.
2. In PowerShell:

```powershell
Get-FileHash ".\VibranceFlow.exe" -Algorithm SHA256
```

3. Confirm the hash matches the value in `VibranceFlow.exe.sha256`.

If Microsoft Defender or another engine flags the binary:

- submit a false-positive report to Microsoft Security Intelligence
- submit the same sample to the vendor that flagged it
- re-check detections after signature/model refresh cycles

## ☕ Support the Project

Modern software distribution has real platform tolls that are difficult for independent open-source projects:

- Windows code-signing certificates (OV/EV): **US$80+/year**
- Apple Developer Program: **US$99/year**
- Google Play Store registration: **US$25** one-time

Support link: [Support VibranceFlow on Ko-fi](https://ko-fi.com/fabio_monreal)

If community funding reaches these milestones, VibranceFlow binaries can be signed and published through official stores/channels (Microsoft, Apple, Google).  
Until then, the focus remains: open-source, free access, transparent security practices, and reproducible local tooling.

## Troubleshooting

- **Mobile cannot connect:** confirm phone and PC are on the same LAN and firewall allows private access.
- **Audio slider is disabled:** the selected app has no active audio session on the PC.
- **Profile not switching:** verify Observer is enabled and the executable is saved in the profile list.

## For developers

Development setup, packaging notes, and contribution rules are documented in [CONTRIBUTING.md](CONTRIBUTING.md) and [packaging/README.md](packaging/README.md).

## License

GPL-3.0 — see [LICENSE](LICENSE).
