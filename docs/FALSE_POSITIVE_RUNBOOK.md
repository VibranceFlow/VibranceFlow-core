# False-positive runbook (Windows EXE)

Maintainer checklist for unsigned VibranceFlow builds. Use this before announcing a public release.

Commercial code signing (OV/EV) and store publishing are planned for a later phase; until then, follow the steps below.

## 1. Build reproducibly

1. Prefer CI builds:
   - Continuous: [`.github/workflows/build-windows.yml`](../.github/workflows/build-windows.yml)
   - Public release: [`.github/workflows/release-windows.yml`](../.github/workflows/release-windows.yml) (tag `v*`, for example `v1.0.1`)
2. Confirm both artifacts ship together:
   - `VibranceFlow.exe`
   - `VibranceFlow.exe.sha256`
3. Never enable **UPX** or third-party packers on the binary.

Local equivalent:

```powershell
poetry install --with packaging
.\packaging\build_windows.ps1
```

## 2. Pre-release VirusTotal scan

1. Upload the **exact** release `VibranceFlow.exe` to [VirusTotal](https://www.virustotal.com).
2. Save the scan URL in the GitHub release notes and README.
3. Record the detection count (for example `2/72`).
4. If more than a few engines flag the file, pause the announcement and continue to step 3 before broad distribution.

Optional A/B (maintainer-only): compare onefile vs one-folder heuristic scores:

```powershell
.\packaging\build_windows_onedir.ps1
```

Upload `dist\VibranceFlow-onedir.dist\VibranceFlow-onedir.exe` to VirusTotal and compare with the onefile build. One-folder avoids Nuitka onefile temp bootstrap extraction, which some engines score higher. Default public format remains **onefile** for install simplicity unless data shows a clear FP win.

## 3. Submit false-positive reports

Submit the **same** release binary (matching published SHA256) to each vendor that flagged it.

### Microsoft Defender / SmartScreen

- Portal: [Microsoft Security Intelligence — file submission](https://www.microsoft.com/en-us/wdsi/filesubmission)
- Category: **Software developer**
- Classification: **Incorrectly detected as malware** / false positive
- Include:
  - GitHub release URL
  - SHA256 from `VibranceFlow.exe.sha256`
  - Short description: open-source Windows display profile switcher; LAN WebSocket for optional mobile remote; no telemetry

### Other vendors (when flagged on VirusTotal)

| Vendor | Submission |
|--------|------------|
| Kaspersky | [https://opentip.kaspersky.com](https://opentip.kaspersky.com) |
| Avast / AVG | [https://www.avast.com/false-positive-file-form.php](https://www.avast.com/false-positive-file-form.php) |
| ESET | [https://support.eset.com/en/kb141-submit-a-file-for-analysis](https://support.eset.com/en/kb141-submit-a-file-for-analysis) |
| Bitdefender | [https://www.bitdefender.com/consumer/support/answer/29358/](https://www.bitdefender.com/consumer/support/answer/29358/) |

Re-scan on VirusTotal **24–72 hours** after submission. Track whether detections drop before promoting the release.

## 4. Publish release

1. Create tag `vX.Y.Z` and push, or run **Release Windows EXE** (`workflow_dispatch`) with the tag name.
2. Verify GitHub Release contains `.exe` + `.sha256`.
3. Paste VirusTotal link and SHA256 into release notes.
4. Update README VirusTotal placeholder with the new scan URL.

## 5. User guidance (do not ask users to disable AV)

Tell users to:

1. Download only from the official GitHub release.
2. Verify SHA256 before running.
3. If SmartScreen appears: **More info** → confirm publisher unknown is expected for unsigned builds → run only after hash check.
4. If Defender quarantines the file: restore from release, verify hash, then submit FP to Microsoft (link above).

Do **not** instruct users to disable Defender or add global exclusions.

## 6. Future: persistent publisher reputation (paid phase)

When budget allows:

1. Purchase **OV** or **EV** code-signing certificate (EV preferred for immediate SmartScreen trust).
2. Sign every release with `signtool` + timestamp server in CI.
3. Re-submit one signed sample to Microsoft — whitelisting often applies to the **certificate publisher**, helping future signed builds.
4. Optional: Microsoft Store / MSIX channel.

Self-signed certificates only trust on machines where the cert was manually installed; they do **not** create public AV whitelist entries for end users.
