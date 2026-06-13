# Packaging VibranceFlow Core

## Windows (Nuitka + optional Microsoft Store)

1. Install Poetry and packaging group: `poetry install --with packaging`
2. Brand assets (committed): `ui/Logos/PNG/logo.png`, `ui/Logos/ICO/logo.ico`
   - Regenerate after logo changes: `poetry run python scripts/generate_brand_assets.py`
3. Build: `.\packaging\build_windows.ps1`
4. Output: `dist/VibranceFlow.exe` + `dist/VibranceFlow.exe.sha256`
5. **Microsoft Store (future / paid):** wrap the built `.exe` with [MSIX Packaging Tool](https://learn.microsoft.com/en-us/windows/msix/packaging-tool/tool-overview), produce `.msixupload`, submit via Partner Center (~US$19 one-time fee + review).

## CI and releases

| Workflow | Trigger | Output |
|----------|---------|--------|
| `build-windows.yml` | `push` to `main`, `workflow_dispatch` | Artifact: `.exe` + `.sha256` |
| `release-windows.yml` | tag `v*`, `workflow_dispatch` | GitHub Release with `.exe` + `.sha256` |

False-positive process: [docs/FALSE_POSITIVE_RUNBOOK.md](../docs/FALSE_POSITIVE_RUNBOOK.md).

## Linux (AppImage — future engine port)

1. Build on Linux with the same Nuitka flow when a Linux display backend exists.
2. Layout `VibranceFlow.AppDir` with `AppRun`, `.desktop`, icon, and binary.
3. Run `appimagetool` to produce `VibranceFlow.AppImage`.
4. User marks executable (`chmod +x`) and runs without root install.

See `build_appimage.sh` skeleton for directory layout.

## Debug local `.exe`

If the release `.exe` exits without showing a window:

1. **Debug build (console + traceback):** `.\packaging\build_windows_debug.ps1` then run `.\dist\VibranceFlow-debug.exe`.
2. **Frozen log file:** packaged builds write to `%APPDATA%\VibranceFlow\app.log` on errors. Override path with `VIBRANCEFLOW_LOG=C:\path\to\log.txt`.
3. **Shared Nuitka flags:** `packaging/nuitka_common.ps1` (GUI + LAN remote: tk-inter, customtkinter, websockets, cryptography, qrcode, pystray, Pillow).
4. **Remote smoke tests:** `poetry run python scripts/test_remote_boot.py` and `scripts/test_prepare_pairing.py` (CI runs both before build).

## Onefile vs one-folder (AV heuristic trade-off)

| Mode | Script | User experience | AV notes |
|------|--------|-----------------|----------|
| **Onefile (default)** | `build_windows.ps1` | Single `VibranceFlow.exe` | Nuitka onefile unpacks to a temp folder at startup; some engines score this higher |
| **One-folder (maintainer test)** | `build_windows_onedir.ps1` | Folder with `.exe` + DLLs | Often fewer heuristic flags; not the default public format |

Policy: **never use UPX** or third-party executable packers.

## Notes

- Build emits:
  - `dist\VibranceFlow.exe`
  - `dist\VibranceFlow.exe.sha256`
- Code signing (OV/EV) is planned for a later funding phase; see README and `docs/FALSE_POSITIVE_RUNBOOK.md`.

## False-positive mitigation checklist

1. Build via GitHub Actions (`build-windows.yml` or `release-windows.yml`).
2. Verify `VibranceFlow.exe` and `VibranceFlow.exe.sha256` are both published in artifact/release.
3. Upload release binary to VirusTotal; save the scan URL in the release.
4. Submit the shipped binary hash + sample to [Microsoft Defender false-positive portal](https://www.microsoft.com/en-us/wdsi/filesubmission).
5. Submit to vendors that flagged the sample in VirusTotal (see runbook).
6. Re-run VirusTotal after signature/model refresh cycles and track detection trend before broad announcement.
