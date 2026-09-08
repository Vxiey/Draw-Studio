# Step 27 — Export / Import Profiles

Draw Studio 1.0.125-beta adds portable one-profile-at-a-time export/import.

## Portable profile format

A profile can be saved as `.drawprofile` (JSON) or normal `.json`.

The current schema is `draw-studio-profile` schema version `1` and contains:

- target/profile name and storage identity
- renderer and quality settings
- CPU/GPU/RAM resource limits
- palette calibration
- tool/exact-color calibration metadata when available
- saved canvas corners and canvas-anchor metadata
- profile UI extras
- application/schema version metadata

## Safety and portability

Profile import is configuration-only and never restores native-input authorization.

The following machine/runtime state is deliberately excluded:

- hardware benchmark / adapter signature
- draw timing calibration
- Auto Tuner feedback
- correction history
- layout-fingerprint cache
- verified-color runtime cache
- target window handles
- target lock, dry-run, preflight or full-draw authorization

Imported canvas/palette/tool metadata is useful as setup metadata, but it never counts as a completed safety check. The target, calibration and normal safety gates must be verified again before real drawing.

## Validation and migration

Before import Draw Studio validates:

- file size and UTF-8 JSON
- Draw Studio profile format/schema
- profile name and target key
- allow-listed settings only
- resource settings
- canvas coordinate shape/range
- palette calibration schema and profile ownership
- calibration JSON structure/depth/size
- absence of machine-specific state

The initial schema-0 prototype is migrated to schema 1. Future unsupported schema versions are rejected instead of guessed.

## Conflict handling

When an imported profile name already exists:

- **Replace** writes only to that profile's isolated settings/calibration files.
- **Import as copy** creates a new local custom profile with its own generated `custom-...` storage key.
- **Cancel** changes nothing.

Calibration ownership metadata is rewritten to the destination storage key when importing as a copy, preventing cross-profile calibration leakage.

## Reset profile

**Reset profile to defaults** removes only the selected profile's saved settings, calibration and learned/profile cache files. Other profiles are untouched.

After reset, shipped profiles return to their target-specific Draw Studio defaults. Custom profiles return to safe generic defaults. Calibration/setup must be verified again.
