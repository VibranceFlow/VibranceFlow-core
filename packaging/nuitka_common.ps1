# Shared Nuitka flags for GUI + LAN remote (Windows). Dot-source from build scripts.
$script:NuitkaCommonArgs = @(
    "--lto=yes"
    "--enable-plugin=tk-inter"
    "--enable-plugin=anti-bloat"
    "--include-package-data=customtkinter"
    "--include-data-dir=ui/Logos=ui/Logos"
    "--include-package=websockets"
    "--include-package=cryptography"
    "--include-package=qrcode"
    "--include-package=pycaw"
    "--include-package=comtypes"
    "--include-package=pystray"
    "--include-package=PIL"
    "--nofollow-import-to=comtypes.test,pulsectl,unittest,pydoc,doctest,distutils"
)

function Get-NuitkaIconArg {
    $icoDir = Join-Path $Root "ui\Logos\ICO"
    foreach ($name in @("app_logo.ico", "logo.ico")) {
        $ico = Join-Path $icoDir $name
        if (Test-Path $ico) {
            return @("--windows-icon-from-ico=$ico")
        }
    }
    $fallback = Get-ChildItem -Path $icoDir -Filter "*.ico" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($fallback) {
        return @("--windows-icon-from-ico=$($fallback.FullName)")
    }
    return @()
}

function Get-NuitkaVersionMetadataArgs {
    $version = if ($env:VIBRANCEFLOW_VERSION) { $env:VIBRANCEFLOW_VERSION } else { "1.0.0" }
    $company = if ($env:VIBRANCEFLOW_COMPANY) { $env:VIBRANCEFLOW_COMPANY } else { "VibranceFlow" }
    $product = if ($env:VIBRANCEFLOW_PRODUCT) { $env:VIBRANCEFLOW_PRODUCT } else { "VibranceFlow" }
    $description = if ($env:VIBRANCEFLOW_FILE_DESCRIPTION) {
        $env:VIBRANCEFLOW_FILE_DESCRIPTION
    } else {
        "Per-game color and audio profile switcher for Windows"
    }
    return @(
        "--windows-company-name=$company"
        "--windows-product-name=$product"
        "--windows-file-description=$description"
        "--windows-product-version=$version"
        "--windows-file-version=$version"
    )
}

function Write-ExecutableSha256 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ExePath
    )
    if (-not (Test-Path $ExePath)) {
        throw "Executable not found: $ExePath"
    }
    $hash = (Get-FileHash $ExePath -Algorithm SHA256).Hash.ToLower()
    $sidecar = "$ExePath.sha256"
    "$hash  $(Split-Path -Leaf $ExePath)" | Out-File -FilePath $sidecar -Encoding ascii
    Write-Host "SHA256: $hash"
    Write-Host "Sidecar: $sidecar"
}
