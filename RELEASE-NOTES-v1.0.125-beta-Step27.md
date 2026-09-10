# Image Draw Bot v1.0.125-beta — Step 27: Export / Import Profiles

Step 27 adds portable, validated profile sharing without weakening Image Draw Bot's existing profile isolation or native-input safety gates.

## New

- Export the currently selected profile as `.drawprofile` or JSON.
- Import portable Image Draw Bot profiles.
- Exported profiles include target identity, renderer settings, CPU/GPU/RAM resource limits, saved canvas metadata, palette calibration, tool calibration and exact-color calibration when available.
- Schema/version metadata with migration of the initial schema-0 prototype to schema 1.
- Strict pre-import validation for format, schema, settings, canvas coordinates and calibration payloads.
- Conflict handling: **Replace**, **Import as copy**, or Cancel.
- Import-as-copy creates a separate `custom-...` storage key and rewrites calibration ownership to that key.
- **Reset profile to defaults** removes only the selected profile's saved settings/calibration/profile caches.

## Isolation and safety

The portable format deliberately excludes machine/runtime state such as:

- hardware benchmark / adapter signature
- draw timing calibration
- Auto Tuner feedback
- correction history
- layout fingerprint cache
- verified-color runtime cache
- target window handles and target geometry runtime state
- target lock, preflight, dry-run and full-draw authorization

Imported calibration never counts as a completed safety check. Image Draw Bot reloads the destination profile in a disarmed configuration-only state, and the normal target/calibration/safety verification remains required before drawing.

## Validation

Windows regression selection:

- Step 27 portability tests: **15/15 passed**
- Combined Step 27 + profile isolation/switch/calibration selection: **30/30 passed**
- `ProfilePortability.py`, `StudioUI.py`, `DrawBot.py`, `GameProfiles.py`, `ProfileStorage.py` and `ProfileIsolation.py` compile successfully.

Step 26 Pixel Accurate, Named Color Intelligence and the CodeQL URL-hostname security hotfix remain included in this release.
