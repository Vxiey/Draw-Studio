# Draw Studio {{VERSION}}

## Release candidate

This is a Draw Studio release-candidate build. The numbered feature roadmap is frozen while RC validation is in progress.

## Download

Use the Windows x64 installer for the normal installation path, or the portable Windows x64 ZIP when you do not want to install the application.

Verify downloaded artifacts against the accompanying `SHA256.txt` file before use.

## RC verification

Before publication, the release workflow must pass:

- Step 30 source release gate
- complete regression discovery
- Draw Studio self-test
- PyInstaller build validation
- Windows ZIP integrity validation
- Inno Setup build validation
- SHA-256 + manifest validation
- silent installer → installed EXE self-test → silent uninstall

## Requirements

- Windows 10/11 x64
- Same privilege level for Draw Studio and the target application; normally both non-admin
- For Gartic Phone: Google Chrome with **Artist Tools for Gartic Phone** installed and enabled

## Safety

CanvasGuard, calibration, target verification, small test, Safety Preflight and Fast Dry Run remain authoritative. RC hardening does not bypass native-input safety gates.

## Known release status

The Windows binaries remain unsigned until Authenticode code signing is configured, so Windows SmartScreen may show a warning.
