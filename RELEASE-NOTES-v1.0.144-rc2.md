# Image Draw Bot v1.0.144-rc2 — Consistent Windows icons

One Image Draw Bot icon now identifies the Windows app and its interface.

- Embed the same multi-resolution icon in ImageDrawBot.exe and Windows Setup.
- Match the app header, window title bars, taskbar, calibration windows and dialogs.
- Match desktop/Start-menu shortcuts and the installed-app listing.
- Use a stable Windows AppUserModelID to group app windows correctly.
- Include icon sizes from 16 to 256 pixels for Windows scaling, with a 512-pixel UI master.
- Preserve the existing rendering and calibration behavior.

Windows release validation includes icon-frame checks and a real Tk/CustomTkinter root/dialog/header integration test, followed by packaging and silent installation/self-test/uninstallation.
