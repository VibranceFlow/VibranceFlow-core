# Contributing to VibranceFlow Core

Thanks for taking the time to contribute.

## Setup

1. Fork and clone [VibranceFlow-core](https://github.com/VibranceFlow/VibranceFlow-core).
2. Use **Python 3.11+ 64-bit** on Windows 11.
3. Install dependencies:

   ```powershell
   poetry install
   ```

   Or: `pip install -r requirements.txt`

4. Copy the example profile:

   ```powershell
   mkdir "$env:APPDATA\VibranceFlow" -ErrorAction SilentlyContinue
   copy profiles.json.example "$env:APPDATA\VibranceFlow\profiles.json"
   ```

5. Run `python gui_main.py` (GUI) or `python main.py` (CLI engine).

## Repository layout (this repo)

| Path | Role |
|------|------|
| `core/` | Engine, profiles, foreground window monitor |
| `core/bindings/` | GDI32 / NVAPI via ctypes |
| `core/remote/` | LAN WebSocket server, Fernet, PIN pairing, firewall helper |
| `ui/` | CustomTkinter GUI, tray, process picker, Pair Mobile dialog |
| `gui_main.py` | GUI entry point |
| `main.py` | CLI entry point |

Architecture write-ups, PoC scripts, and platform experiments are maintained in [VibranceFlow-PoC](https://github.com/VibranceFlow/VibranceFlow-PoC).

## Guidelines

- Keep user-facing strings, comments, and logs in **English**.
- Prefer small, focused pull requests.
- Match existing style (typed hints, dataclasses, minimal dependencies).
- The engine should call GDI/NVAPI only when the foreground executable changes.
- `WindowsDisplayManager.shutdown()` must restore the baseline captured at startup.

## Pull requests

1. For larger changes, open an issue first.
2. Branch from `main`: `git checkout -b feature/short-description`.
3. Test on Windows; use an NVIDIA GPU when touching display code.
4. Update `README.md` if setup or behavior changes.
5. Describe what you tested in the PR body.

## Bug reports

Please include:

- Windows version, GPU model, driver version
- `python --version`
- Steps to reproduce
- Console log output
- Whether NVAPI is available or GDI-only

## Related repositories

| Repo | Role |
|------|------|
| [VibranceFlow-PoC](https://github.com/VibranceFlow/VibranceFlow-PoC) | Docs and validation scripts |
| [VibranceFlow-mobile](https://github.com/VibranceFlow/VibranceFlow-mobile) | Mobile control (planned) |
| [VibranceFlow-web](https://github.com/VibranceFlow/VibranceFlow-web) | Web site (planned) |

## Questions

Open an issue or discussion on [VibranceFlow-core](https://github.com/VibranceFlow/VibranceFlow-core).
