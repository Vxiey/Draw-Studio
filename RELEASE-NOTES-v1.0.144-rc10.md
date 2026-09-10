# Image Draw Bot v1.0.144-rc10 — Compact UI and release update fix

- Reduce the default sidebar density with progressive-disclosure sections while keeping the five-step workflow and all existing controls.
- Keep target selection, image loading, one-click setup, core drawing preset and preview/draw actions visible first.
- Move profile/ink extras, image automation, manual calibration, fine tuning, preview options and duplicate safety shortcuts behind clear expandable sections.
- Keep Advanced and Developer controls available, but start the largest groups collapsed so the settings panel is easier to scan.
- Preserve the existing Tk variables, callbacks, saved profile values and profile-scoped visibility; the compact layer only changes presentation.
- Add regression coverage for compact UI structure, compatibility markers and profile-aware visibility.
- Publish this as a new rc10 installer so rc9 installations can detect the update through the existing verified GitHub Releases updater.

The updater security model is unchanged: automatic installation still requires a versioned GitHub Release, the expected installer filename, published SHA-256 digest and size checks before launch.
