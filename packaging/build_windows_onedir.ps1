# Optional one-folder build for AV heuristic comparison (no onefile temp bootstrap).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. (Join-Path $PSScriptRoot "nuitka_common.ps1")

poetry install --with packaging

$outName = "VibranceFlow-onedir"
poetry run python -m nuitka `
  --standalone `
  --windows-console-mode=disable `
  --assume-yes-for-downloads `
  --output-dir=dist `
  --output-filename=$outName `
  @((Get-NuitkaVersionMetadataArgs)) `
  @NuitkaCommonArgs `
  @((Get-NuitkaIconArg)) `
  gui_main.py

$exePath = Join-Path $Root "dist\$outName.dist\$outName.exe"
Write-ExecutableSha256 -ExePath $exePath
Write-Host "One-folder build finished. Run: $exePath"
