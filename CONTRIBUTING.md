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

### Remote / pairing (dev)

```powershell
# With GUI open (Pair Mobile or keep port on):
poetry run python scripts/diagnose_lan_remote.py

poetry run python scripts/test_remote_boot.py
poetry run python scripts/test_prepare_pairing.py
poetry run python scripts/verify_protocol_v1.py

# PIN like the Android app (use code from Pair Mobile):
poetry run python scripts/test_pair_pin_client.py --host 192.168.1.2 --pin 123456

# Fernet session (Pair Mobile -> Copy JSON -> pairing.json):
poetry run python scripts/ws_remote_client.py --pairing pairing.json --demo
```

Cross-repo Fernet check (run export in **VibranceFlow-mobile** first):

```powershell
cd ..\VibranceFlow-mobile
npx tsx scripts/test-fernet-cmds-export.ts
cd ..\VibranceFlow-core
poetry run python scripts/test_fernet_cmds.py
```

- Pair Mobile starts the server via `prepare_pairing_session()`; firewall UAC is optional (**Allow in Firewall** in the dialog).
- Do not run the full app as administrator for remote testing — only the firewall helper may request elevation.
- Frozen builds log to `%APPDATA%\VibranceFlow\app.log` (override with `VIBRANCEFLOW_LOG`).
- **Mobile APK compatibility:** core changes that keep LAN protocol **v1** (port 8765, Fernet wire, commands) do not require a new APK. See [VibranceFlow-mobile/docs/CORE_APK_COMPATIBILITY.md](https://github.com/VibranceFlow/VibranceFlow-mobile/blob/main/docs/CORE_APK_COMPATIBILITY.md).

## Repository layout (this repo)

| Path | Role |
|------|------|
| `core/` | Engine, profiles, foreground window monitor |
| `core/bindings/` | GDI32 / NVAPI via ctypes |
| `core/remote/` | LAN WebSocket server, Fernet, PIN/QR pairing, firewall helper |
| `core/single_instance.py` | Windows mutex — one GUI instance |
| `ui/` | CustomTkinter GUI, tray, process picker, Pair Mobile dialog |
| `ui/window_chrome.py` | Non-maximizable windowed mode |
| `ui/layout.py` | Screen-aware window / pairing dialog sizing |
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
| [VibranceFlow-mobile](https://github.com/VibranceFlow/VibranceFlow-mobile) | Android/iOS LAN remote |
| [VibranceFlow-web](https://github.com/VibranceFlow/VibranceFlow-web) | Landing site |

## Questions

Open an issue or discussion on [VibranceFlow-core](https://github.com/VibranceFlow/VibranceFlow-core).
