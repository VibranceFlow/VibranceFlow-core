#!/usr/bin/env bash
# Skeleton AppImage build (run on Linux when a Linux engine port exists).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

poetry install --with packaging
# Mirror packaging/nuitka_common.ps1 flags when Linux GUI port is ready.
poetry run python -m nuitka --standalone --output-dir=dist/linux \
  --enable-plugin=tk-inter \
  --include-package-data=customtkinter \
  --include-data-dir=ui/Logos=ui/Logos \
  --include-package=websockets \
  --include-package=cryptography \
  --include-package=qrcode \
  --nofollow-import-to=comtypes.test,pulsectl \
  gui_main.py

APP_DIR="$ROOT/dist/VibranceFlow.AppDir"
mkdir -p "$APP_DIR/usr/bin"
cp dist/linux/gui_main.bin "$APP_DIR/usr/bin/VibranceFlow" 2>/dev/null || true

cat > "$APP_DIR/VibranceFlow.desktop" <<'EOF'
[Desktop Entry]
Name=VibranceFlow
Exec=AppRun
Icon=VibranceFlow
Type=Application
Categories=Settings;
EOF

cp ui/Logos/PNG/*.png "$APP_DIR/VibranceFlow.png" 2>/dev/null || true
echo '#!/bin/sh
DIR="$(dirname "$(readlink -f "$0")")"
exec "$DIR/usr/bin/VibranceFlow" "$@"' > "$APP_DIR/AppRun"
chmod +x "$APP_DIR/AppRun"

appimagetool "$APP_DIR" dist/VibranceFlow.AppImage
echo "Created dist/VibranceFlow.AppImage"
