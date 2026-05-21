# LuminaSync Core

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)

Windows desktop app that applies per-game color profiles (vibrance, brightness, contrast, gamma, hue) when a configured executable is in focus, and restores desktop settings when you switch away.

Part of the [LuminaSync](https://github.com/LuminaSync) open-source ecosystem:

| Repository | Purpose |
|------------|---------|
| [LuminaSync-core](https://github.com/LuminaSync/LuminaSync-core) | Windows engine + GUI (this repo) |
| [LuminaSync-mobile](https://github.com/LuminaSync/LuminaSync-mobile) | Mobile remote control (planned) |
| [LuminaSync-web](https://github.com/LuminaSync/LuminaSync-web) | Marketing / docs site on Vercel (planned) |

## Requirements

- Windows 11 (validated in PoC)
- Python 3.11+ **64-bit**
- NVIDIA desktop GPU with Digital Vibrance in the driver (optional; GDI works without NVAPI)

## Quick start

```powershell
cd path\to\LuminaSync-core
pip install -r requirements.txt
mkdir "$env:APPDATA\LuminaSync" -ErrorAction SilentlyContinue
copy profiles.json.example "$env:APPDATA\LuminaSync\profiles.json"
```

### GUI (recommended)

```powershell
python gui_main.py
```

- **Add** — fast process list; icon preview on selection
- **Manual** — pick a `.exe` from disk
- Color sliders appear **only** after selecting a program
- **Minimize** → system tray (double-click tray icon to open; **Quit** in menu exits)
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

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). For AI-assisted development in Cursor, see [AGENTS.md](AGENTS.md).

```
core/
  bindings/       # GDI32 + NVAPI (ctypes)
  display_manager.py
  profile_manager.py
  window_monitor.py
  engine.py
ui/               # CustomTkinter GUI + tray
gui_main.py
main.py
scripts/          # Historical PoCs (local validation)
```

## Contributing

We welcome issues and pull requests. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR.

For org remotes and moving this repo into `LuminaSync-core` under a parent workspace, see [docs/WORKSPACE.md](docs/WORKSPACE.md).

## License

GPL-3.0 — see [LICENSE](LICENSE).
