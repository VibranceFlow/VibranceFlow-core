# Build VibranceFlow Windows executable with Nuitka (requires Poetry + packaging).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. (Join-Path $PSScriptRoot "nuitka_common.ps1")

poetry install --with packaging
$Ico = Get-ChildItem -Path "ui\Logos\ICO\*.ico" -ErrorAction SilentlyContinue | Select-Object -First 1
$IconArg = @()
if ($Ico) { $IconArg = @("--windows-icon-from-ico=$($Ico.FullName)") }
$Version = if ($env:VIBRANCEFLOW_VERSION) { $env:VIBRANCEFLOW_VERSION } else { "1.0.0" }
$Company = if ($env:VIBRANCEFLOW_COMPANY) { $env:VIBRANCEFLOW_COMPANY } else { "VibranceFlow" }
$Product = if ($env:VIBRANCEFLOW_PRODUCT) { $env:VIBRANCEFLOW_PRODUCT } else { "VibranceFlow" }
$FileDescription = if ($env:VIBRANCEFLOW_FILE_DESCRIPTION) { $env:VIBRANCEFLOW_FILE_DESCRIPTION } else { "Per-game color and audio profile switcher for Windows" }

poetry run python -m nuitka `
  --standalone `
  --onefile `
  --windows-console-mode=disable `
  --assume-yes-for-downloads `
  --output-dir=dist `
  --output-filename=VibranceFlow `
  --windows-company-name="$Company" `
  --windows-product-name="$Product" `
  --windows-file-description="$FileDescription" `
  --windows-product-version="$Version" `
  --windows-file-version="$Version" `
  @NuitkaCommonArgs `
  @IconArg `
  gui_main.py

$Hash = (Get-FileHash "dist\VibranceFlow.exe" -Algorithm SHA256).Hash.ToLower()
"$Hash  VibranceFlow.exe" | Out-File -FilePath "dist\VibranceFlow.exe.sha256" -Encoding ascii

Write-Host "Build finished. See dist\VibranceFlow.exe"
