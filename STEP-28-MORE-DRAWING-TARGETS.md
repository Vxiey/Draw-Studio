# Step 28 — More Drawing Targets

Step 28 makes drawing-target support explicit and extensible while preserving Image Draw Bot's fail-closed calibration model.

## Architecture

`TargetCapabilities.py` is a data-only registry. It never stores coordinates, target handles, mouse authorization or palette pixels.

Each target declares:

- stable profile key
- display name
- target kind
- setup mode
- palette mode
- whether the target is timed
- whether layout fingerprints are supported
- whether per-profile timing data is supported

## Setup modes

### `paint-auto`

Reserved for Microsoft Paint's verified visual setup detector.

### `browser-auto`

Only targets with an existing deterministic and regression-tested browser canvas/palette detector use this mode.

Current verified browser-auto keys:

- `gartic-phone`
- `skribbl`
- `skribbl-fast`
- `sketchheads`
- `sketchful`

### `manual`

Targets without a verified detector use explicit user calibration. This is deliberate rather than a reduced-safety fallback.

Current dedicated manual browser keys include:

- `drawize`
- `gartic-io`
- `kleki`
- `magma`

Custom profiles also fail safely to manual semantics.

## Kleki

Profile key: `kleki`

Kleki gets its own profile defaults, Profile Engine policy, AppTools capability record and profile-specific storage namespace. Brush, Fill and Eraser semantics are supported, but their screen positions are always calibrated by the user.

## Magma

Profile key: `magma`

Magma gets a separate collaborative-browser profile with the same isolation guarantees. Because collaborative UI panels and canvas layouts can change, automatic screen-coordinate assumptions are intentionally not made.

## Profile isolation

All target-specific persisted data continues to derive from the profile key. In particular, these paths remain distinct per target:

- settings
- palette calibration
- timing calibration
- layout fingerprint cache
- verified custom-color cache
- application-tool calibration

`kleki` and `magma` therefore cannot inherit Gartic/Skribbl/Paint calibration data.

## UI scopes

Step 28 adds semantic UI scopes:

- `browser` — any browser drawing target
- `browser-auto` — a browser target with a verified automatic detector
- `browser-manual` — a dedicated browser target requiring manual setup
- `oneclick` — targets that support the Step 27.5 One-click Setup action

This allows manual browser targets to keep normal calibration controls without displaying misleading automatic setup controls.

## Relationship to Step 27.5

Step 27.5 remains the verification layer for One-click Setup. Its target mode now consults the Step 28 capability registry instead of maintaining another hard-coded target list.

Adding a new profile to the registry does **not** automatically make it One-click capable. A target must explicitly be promoted to `browser-auto` only after its detector is implemented and verified with regression fixtures/current UI captures.

## Safety invariants

Step 28 does not change these rules:

- profile policies cannot arm native input
- no target coordinates live in profile defaults/policies
- manual calibration remains anchored and profile-owned
- target/canvas verification remains required by the existing execution path
- CanvasGuard remains authoritative for every native drawing action
- profile switches clear incompatible session state

## Verification

The Step 28 Windows regression selection passed **59/59 tests**, including target registry behavior, new target isolation, Step 27.5 compatibility, profile switching, calibration/timing storage isolation, Profile Engine constraints and UI metadata/defaults.
