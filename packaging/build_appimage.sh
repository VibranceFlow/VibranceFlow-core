#!/usr/bin/env bash
# Skeleton AppImage build (run on Linux when a Linux engine port exists).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

poetry install --with packaging
poetry run python -m nuitka --standalone --output-dir=dist/linux gui_main.py

APP_DIR="$ROOT/dist/LuminaSync.AppDir"
mkdir -p "$APP_DIR/usr/bin"
cp dist/linux/gui_main.bin "$APP_DIR/usr/bin/luminasync" 2>/dev/null || true

cat > "$APP_DIR/luminasync.desktop" <<'EOF'
[Desktop Entry]
Name=LuminaSync
Exec=AppRun
Icon=luminasync
Type=Application
Categories=Settings;
EOF

cp ui/Logos/PNG/*.png "$APP_DIR/luminasync.png" 2>/dev/null || true
echo '#!/bin/sh
DIR="$(dirname "$(readlink -f "$0")")"
exec "$DIR/usr/bin/luminasync" "$@"' > "$APP_DIR/AppRun"
chmod +x "$APP_DIR/AppRun"

appimagetool "$APP_DIR" dist/LuminaSync.AppImage
echo "Created dist/LuminaSync.AppImage"
