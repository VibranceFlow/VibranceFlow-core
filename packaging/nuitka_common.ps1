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
    "--nofollow-import-to=comtypes.test,pulsectl"
)
