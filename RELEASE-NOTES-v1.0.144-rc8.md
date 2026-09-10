# Image Draw Bot v1.0.144-rc8 — Use the prepared image colors

Pixel Accurate previously bypassed the image-specific RGB palette and mapped the image to the standard toolbar palette. Saving a picture palette also left the old preview and exact-color status on screen.

- Use one ordered image RGB palette for Pixel Accurate mapping, correction simulation, previews and runtime color selectors.
- Use the prepared palette in the normal color-run planner too; keep it isolated to the same image and Microsoft Paint profile.
- Build picture colors from measured source clusters without substituting standard palette colors. Invalidate older picture-palette analysis caches.
- Refresh RGB calibration status and invalidate the old preview after picture-palette preparation.
- Stop if an exact image color cannot be selected instead of silently substituting a standard palette color.
- Retain + saving, one open dialog for the batch and at least 750 ms between additions.

After updating: select Microsoft Paint, run Custom color palette for picture again, then Build preview. The custom palette is still a limited-color approximation of a photograph. Native Paint behavior and swatch insertion require a real run on the target Paint version.

Regression coverage checks source-to-input RGB values, both rendering paths, runtime selectors, missing calibration, stale preview invalidation and image/profile isolation.
