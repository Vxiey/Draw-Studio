# Step 9 — Calibration State + Profile-Isolated Cache

Image Draw Bot now treats calibration and learned runtime data as profile-owned state.

## Calibration states

Palette setup is reported as one of:

- **Unavailable** — no saved palette and no trusted preset.
- **Estimated** — a built-in preset exists, but the current target layout has not been verified.
- **Calibrated** — the palette was captured/reviewed for this profile.
- **Verified** — the current palette was screen-verified by automatic calibration or a verified layout restore.

The UI no longer treats a built-in preset as equivalent to a verified current palette.

## Profile isolation

Paint, Gartic Phone, Skribbl and other profiles use separate persistent storage for:

- palette calibration
- settings
- browser layout fingerprints
- learned draw-time calibration
- verified exact-color cache
- application tool calibration

Microsoft Paint also uses a dedicated `paint-tools-microsoft-paint.json` tool file. Existing anchored `paint-tools.json` data is migrated safely on first use.

## Timing isolation

Learned timing is stored per profile and additionally keyed by:

- speed
- precision
- region-fill mode
- effective tool
- brush width
- custom-color workflow

Changing from Paint Pencil 1 px to Brush 5 px, or from calibrated palette to Adaptive Exact, therefore cannot reuse an unrelated learned timing model.

## Verified-color cache safety

Persistent verified Paint colors are bound to a calibration-context fingerprint built from the active profile's palette, tools and exact-color controls. Recalibrating any of those invalidates stale verified colors automatically without deleting another profile's cache.

## Browser layout cache

Layout fingerprints are now written to separate per-profile files. A cached layout is still sampled against the live palette before it is restored, and a successful restore writes a **Verified** palette state for that same profile only.
