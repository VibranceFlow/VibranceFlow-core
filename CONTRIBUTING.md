# Contributing to LuminaSync Core

Thank you for helping improve LuminaSync. This document covers setup, conventions, and how to submit changes.

## Code of conduct

Be respectful and constructive. Focus on technical merit and user impact.

## Development setup

1. Fork and clone [LuminaSync-core](https://github.com/LuminaSync/LuminaSync-core).
2. Use **Python 3.11+ 64-bit** on Windows 11.
3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Copy the example profile:

   ```powershell
   mkdir "$env:APPDATA\LuminaSync" -ErrorAction SilentlyContinue
   copy profiles.json.example "$env:APPDATA\LuminaSync\profiles.json"
   ```

5. Run the GUI: `python gui_main.py` or the CLI engine: `python main.py`.

## Project layout

| Path | Role |
|------|------|
| `core/` | Display engine, profiles, foreground window monitor |
| `core/bindings/` | Low-level GDI32 / NVAPI via ctypes (no extra native deps) |
| `ui/` | CustomTkinter GUI, tray, process picker |
| `docs/` | Architecture, roadmap, PoC notes |
| `scripts/` | Standalone PoC scripts (not required for the app) |

## Conventions

- **Language**: English for user-facing strings, docstrings, comments, logs, and documentation.
- **Scope**: Small, focused PRs. Do not refactor unrelated code.
- **Style**: Match existing patterns (dataclasses, typed hints, minimal dependencies).
- **Performance**: The engine polls every ~1s; avoid NVAPI/GDI calls unless the foreground exe changes.
- **Safety**: `WindowsDisplayManager.shutdown()` must restore the baseline captured at startup.

## Pull request process

1. Open an issue for larger changes (new features, breaking behavior).
2. Branch from `main`: `git checkout -b feature/short-description`.
3. Test on Windows with an NVIDIA GPU if your change touches display code.
4. Update `docs/` or `README.md` when behavior or setup changes.
5. Open a PR with a clear description and test steps.

## Reporting bugs

Include:

- Windows version, GPU model, driver version
- Python version (`python --version`)
- Steps to reproduce
- Relevant log output from console
- Whether NVAPI or GDI-only path is in use

## Related repositories

- [LuminaSync-mobile](https://github.com/LuminaSync/LuminaSync-mobile) — future remote control
- [LuminaSync-web](https://github.com/LuminaSync/LuminaSync-web) — future Vercel site

API contracts between repos are not finalized yet; coordinate via issues in this repo.

## Questions

Open a [GitHub Discussion](https://github.com/LuminaSync/LuminaSync-core/discussions) or issue if unsure before a large PR.
