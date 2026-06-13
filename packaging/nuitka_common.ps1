# Shared Nuitka flags for GUI + LAN remote (Windows). Dot-source from build scripts.
$script:NuitkaCommonArgs = @(
    "--enable-plugin=tk-inter"
    "--include-package-data=customtkinter"
    "--include-data-dir=ui/Logos=ui/Logos"
    "--include-package=websockets"
    "--include-package=cryptography"
    "--include-package=qrcode"
    "--include-package=pycaw"
    "--include-package=comtypes"
    "--include-package=pystray"
    "--include-package=PIL"
    "--nofollow-import-to=comtypes.test,pulsectl"
)

function Get-NuitkaIconArg {
    $ico = Get-ChildItem -Path "ui\Logos\ICO\*.ico" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($ico) {
        return @("--windows-icon-from-ico=$($ico.FullName)")
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
