# Packaging VibranceFlow Core

## Windows (Nuitka + optional Microsoft Store)

1. Install Poetry and packaging group: `poetry install --with packaging`
2. Build: `.\packaging\build_windows.ps1`
3. Output: `dist/VibranceFlow.exe` (standalone folder or onefile per script flags)
4. **Microsoft Store:** wrap the built `.exe` with [MSIX Packaging Tool](https://learn.microsoft.com/en-us/windows/msix/packaging-tool/tool-overview), produce `.msixupload`, submit via Partner Center (~US$19 one-time fee + review).

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
3. **Shared Nuitka flags:** `packaging/nuitka_common.ps1` (GUI + LAN remote: tk-inter, customtkinter, websockets, cryptography, qrcode).
4. **Remote smoke tests:** `poetry run python scripts/test_remote_boot.py` and `scripts/test_prepare_pairing.py` (CI runs both before build).

## Notes

- Build now emits:
  - `dist\VibranceFlow.exe`
  - `dist\VibranceFlow.exe.sha256`
- Sign Windows binaries before public distribution when possible.

## False-positive mitigation checklist

1. Build via GitHub Actions workflow `build-windows.yml`.
2. Verify `VibranceFlow.exe` and `VibranceFlow.exe.sha256` are both published in artifact/release.
3. Submit the shipped binary hash + sample to Microsoft Defender false-positive portal.
4. Submit to vendors that flagged the sample in VirusTotal.
5. Re-run VirusTotal after signature updates and track detection trend before broad announcement.
