# Signs the frozen app and the compiled installer with Authenticode.
#
# CANNOT be tested in this Linux dev sandbox -- signtool.exe ships with
# the Windows SDK and only runs on Windows, and there is no real
# code-signing certificate available here anyway. This is a real,
# correct, but UNCONFIGURED template: fill in $CertPath/$CertPassword
# (or switch to a hardware token / EV certificate's own signing flow,
# which usually doesn't take a password at all) before running it.
#
# Why this step matters, per docs/architecture.md §7: PyInstaller binaries
# routinely trip Windows SmartScreen and antivirus heuristics purely for
# being unsigned, freshly-built executables. Signing both the inner
# PhotoToCAD.exe and the outer installer .exe is the mitigation, not an
# optional polish step.
#
# Run from the project root, after both app.spec and installer.iss have
# already produced their outputs:
#   powershell -ExecutionPolicy Bypass -File packaging\sign.ps1

$ErrorActionPreference = "Stop"

# ---- fill these in -------------------------------------------------
$CertPath = "C:\path\to\your-cert.pfx"
$CertPassword = "REPLACE_ME"
$TimestampUrl = "http://timestamp.digicert.com"
# ----------------------------------------------------------------------

$signtool = Get-ChildItem -Path "C:\Program Files (x86)\Windows Kits\10\bin" `
    -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -like "*x64*" } |
    Select-Object -First 1 -ExpandProperty FullName

if (-not $signtool) {
    throw "signtool.exe not found. Install the Windows SDK, or set `$signtool manually."
}

$appExe = "packaging\dist\PhotoToCAD\PhotoToCAD.exe"
$installerExe = Get-ChildItem "packaging\installer_output\*.exe" |
    Select-Object -First 1 -ExpandProperty FullName

foreach ($target in @($appExe, $installerExe)) {
    if (-not (Test-Path $target)) {
        throw "Nothing to sign at '$target' -- build it first (see app.spec / installer.iss)."
    }
    & $signtool sign /f $CertPath /p $CertPassword /fd SHA256 /tr $TimestampUrl /td SHA256 $target
    if ($LASTEXITCODE -ne 0) {
        throw "signtool failed on '$target' (exit code $LASTEXITCODE)."
    }
    Write-Host "Signed: $target"
}
