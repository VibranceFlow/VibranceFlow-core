# Debug build: console visible + shared Nuitka flags (capture tracebacks).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. (Join-Path $PSScriptRoot "nuitka_common.ps1")

poetry install --with packaging
$Ico = Get-ChildItem -Path "ui\Logos\ICO\*.ico" -ErrorAction SilentlyContinue | Select-Object -First 1
$IconArg = @()
if ($Ico) { $IconArg = @("--windows-icon-from-ico=$($Ico.FullName)") }

poetry run python -m nuitka `
  --onefile `
  --windows-console-mode=force `
  --assume-yes-for-downloads `
  --output-dir=dist `
  --output-filename=VibranceFlow-debug `
  @NuitkaCommonArgs `
  @IconArg `
  gui_main.py

Write-Host "Debug build finished. Run: .\dist\VibranceFlow-debug.exe"
