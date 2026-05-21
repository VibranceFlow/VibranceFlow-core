# Build LuminaSync Windows executable with Nuitka (requires Poetry + packaging group).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

poetry install --with packaging
$Ico = Get-ChildItem -Path "ui\Logos\ICO\*.ico" -ErrorAction SilentlyContinue | Select-Object -First 1
$IconArg = @()
if ($Ico) { $IconArg = @("--windows-icon-from-ico=$($Ico.FullName)") }

poetry run python -m nuitka `
  --standalone `
  --onefile `
  --assume-yes-for-downloads `
  --output-dir=dist `
  --output-filename=LuminaSync `
  --include-package=core `
  --include-package=ui `
  --include-package=customtkinter `
  --include-package=websockets `
  --include-package=cryptography `
  --include-package=qrcode `
  @IconArg `
  gui_main.py

Write-Host "Build finished. See dist\LuminaSync.exe"
