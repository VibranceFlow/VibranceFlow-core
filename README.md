# LuminaSync Core

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)

Windows desktop app that applies per-game color profiles (vibrance, brightness, contrast, gamma, hue) when a configured executable is in focus, and restores desktop settings when you switch away.

Part of the [LuminaSync](https://github.com/LuminaSync) open-source ecosystem:

| Repository | Purpose |
|------------|---------|
| [LuminaSync-core](https://github.com/LuminaSync/LuminaSync-core) | Windows engine + GUI (this repo) |
| [LuminaSync-PoC](https://github.com/LuminaSync/LuminaSync-PoC) | Validation scripts, architecture notes, experiments |
| [LuminaSync-mobile](https://github.com/LuminaSync/LuminaSync-mobile) | Android/iOS remote (Expo, LAN WebSocket) |
| [LuminaSync-web](https://github.com/LuminaSync/LuminaSync-web) | Site on Vercel (planned) |

## Requirements

- Windows 11
- Python 3.11+ **64-bit**
- NVIDIA desktop GPU with Digital Vibrance in the driver (optional; GDI works without NVAPI)

## Quick start

### Poetry (recommended)

```powershell
cd path\to\LuminaSync-core
poetry install
mkdir "$env:APPDATA\LuminaSync" -ErrorAction SilentlyContinue
copy profiles.json.example "$env:APPDATA\LuminaSync\profiles.json"
poetry run python gui_main.py
```

### pip

```powershell
pip install -r requirements.txt
mkdir "$env:APPDATA\LuminaSync" -ErrorAction SilentlyContinue
copy profiles.json.example "$env:APPDATA\LuminaSync\profiles.json"
```

### GUI (recommended)

```powershell
python gui_main.py
```

- **Add** — running process list with icon preview on selection
- **Manual** — pick a `.exe` from disk
- Color sliders appear only after selecting a program; **Reset** restores that program’s profile to GPU defaults captured at startup
- **Pair Mobile** — LAN IP + 6-digit code or QR (Fernet); optional **Keep remote port open (8765)** in settings
- PC UI syncs when the phone changes profiles; `get_state` includes saved `programs[]` for the mobile app
- **Minimize** → system tray (double-click the icon to open; **Quit** in the menu exits)
- **Close (X)** → exits the application
- **Start with Windows** → Run registry entry with `--tray` (starts minimized to tray)

```powershell
python gui_main.py --tray
```

### CLI engine (no GUI)

```powershell
python main.py
```

## Profiles (`profiles.json`)

NVIDIA Control Panel–style units:

| Field | Description |
|-------|-------------|
| `vibrance` | 0–100 (%) |
| `brightness` | offset % (e.g. `42` = +42%) |
| `contrast` | offset % |
| `gamma` | 0.4–2.8 |
| `hue` | degrees 0–359 (optional) |

Stored at `%APPDATA%\LuminaSync\profiles.json` (see `profiles.json.example`).

## How it works

A background thread polls the foreground window about once per second. When the executable matches a configured profile, display settings are applied via GDI gamma LUT (brightness, contrast, gamma) and NVAPI (vibrance, hue). Otherwise the desktop profile is applied, or the original baseline is restored if the observer is disabled.

```
core/
  bindings/         # GDI32 + NVAPI (ctypes)
  remote/           # LAN WebSocket + Fernet for mobile
  display_manager.py
  profile_manager.py
  window_monitor.py
  engine.py
ui/                 # CustomTkinter GUI + system tray
scripts/
  ws_remote_client.py   # test remote API without a phone
packaging/          # Nuitka / MSIX / AppImage notes
gui_main.py
main.py
```

### Mobile remote testing (no Android app)

1. Open the GUI → **Pair Mobile** → **Copy JSON** (or scan QR later from the mobile app).
2. In another terminal:

```powershell
poetry run python scripts/ws_remote_client.py --pairing pairing.json --demo
```

Or pass `--host`, `--port`, and `--key` from the JSON. Interactive mode omits `--demo`.

Allow LuminaSync through the Windows firewall on **private** networks when prompted.

Deeper design notes and Win11/NVAPI validation live in [LuminaSync-PoC](https://github.com/LuminaSync/LuminaSync-PoC). Packaging: [packaging/README.md](packaging/README.md).

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

GPL-3.0 — see [LICENSE](LICENSE).
