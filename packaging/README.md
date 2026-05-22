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

## Notes

- Include `customtkinter`, `websockets`, `cryptography`, and `qrcode` in Nuitka `--include-package` flags.
- Sign Windows binaries before Store submission when possible.
