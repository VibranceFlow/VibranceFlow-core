# Debug build: console visible + shared Nuitka flags (capture tracebacks).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. (Join-Path $PSScriptRoot "nuitka_common.ps1")

poetry install --with packaging

poetry run python -m nuitka `
  --standalone `
  --onefile `
  --windows-console-mode=force `
  --assume-yes-for-downloads `
  --output-dir=dist `
  --output-filename=VibranceFlow-debug `
  @NuitkaCommonArgs `
  @((Get-NuitkaIconArg)) `
  gui_main.py

Write-Host "Debug build finished. Run: .\dist\VibranceFlow-debug.exe"
