# Image Draw Bot v1.0.144-rc1 — Automatic Image Drawing

This release completes the public rebrand from **Draw Studio** to **Image Draw Bot** while preserving upgrade compatibility.

## Rebrand

- Product name: **Image Draw Bot**
- Tagline: **Automatic Image Drawing**
- Repository: `Vxiey/Image-Draw-Bot`
- Windows executable: `ImageDrawBot.exe`
- Installer/ZIP/checksum/manifest artifacts use the `ImageDrawBot-` prefix.
- UI, calibration windows, launcher text, Windows file metadata and release titles use the new brand.

## Compatibility

- Inno Setup AppId is unchanged, so installed Draw Studio copies upgrade in place.
- Existing `%LOCALAPPDATA%\DrawBotStudio` settings/calibrations are copied to `%LOCALAPPDATA%\ImageDrawBot` on first frozen run; the old directory remains untouched as a fallback.
- The new updater recognizes both `ImageDrawBot.exe` and legacy `DrawStudio.exe` installations.
- A legacy-named Setup alias is published for older updater clients during the transition.

## Paint behavior

Current Paint safety fixes remain intact, including the rule that sketch/single-color modes do not open Edit colors.
