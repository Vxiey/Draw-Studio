# Automatic Paint preparation

Load an image, select Microsoft Paint, then press **Prepare Paint & draw**.
Before each full drawing, Image Draw Bot opens Paint if none is visible, activates
it, selects Pencil and a verified 1 px size, identifies the blank visible canvas
and palette, and discovers the current Edit colors RGB fields and OK button.
The dialog is dismissed with Cancel after calibration. The existing Adaptive
Exact renderer uses the fresh RGB coordinates for colors that need a custom
match. Tests, preview, setup locking, preflight and dry-run diagnostics are
optional for Paint. Other profiles retain their existing start flow.

**Prepare Paint automatically** performs the same preparation without starting
a drawing. It does not create, clear, resize or replace a document. Keep one
Paint window with the whole blank canvas visible. Multiple Paint windows,
covered controls, a nonblank/clipped canvas or ambiguous fields stop preparation
with a status message. Stop, image changes and profile changes revoke a pending
start. Live target geometry and guarded mouse checks still run during drawing.

## Compatibility

The automatic control matcher supports Swedish and English accessible control
names in modern Windows Paint. RGB mode is required in Edit colors. It reads
labels/control rectangles rather than using the supplied screenshots as fixed
click coordinates. Other languages, themes or Paint versions may need manual
calibration; unsupported automatic preparation does not guess controls. Manual
calibration and diagnostic controls remain available, but the automatic Start
path always requires successful fresh preparation.

Windows UI Automation is accessed through the system Windows PowerShell and
.NET assemblies; no new Python dependency is required. The subprocess is bounded
and cancellable. Reference:
[Microsoft AutomationElement.FromHandle](https://learn.microsoft.com/en-us/dotnet/api/system.windows.automation.automationelement.fromhandle)
and [InvokePattern](https://learn.microsoft.com/en-us/dotnet/api/system.windows.automation.invokepattern).

## Validation scope

The supplied 1920 x 1048 Paint screenshot detects 20 palette colors, Pencil,
Fill, Eraser and an inset canvas rectangle (77, 227, 1843, 994). Tests cover
Swedish/English RGB labels, negative monitor coordinates, ambiguous fields,
window startup, control ordering, and cancellation/stale-start behavior. Windows
CI parses the embedded PowerShell without sending desktop input.

Live end-to-end UI Automation and RGB delivery on the user's Paint version
remain to be validated. Screenshot recognition and mock-backed control tests
are not a claim of a completed real Paint drawing.

Local regression result: 1,329 tests ran in 82.815 s, OK (one Windows-only parser test skipped on Linux).

## Custom color palette for picture

With a source image loaded, **Custom color palette for picture** uses the same bounded image-color planner as rendering to choose important Paint RGB colors. It calibrates Edit colors numeric R/G/B fields automatically if necessary, enters the required custom colors, and saves the resulting picture palette by source-image and Paint-calibration fingerprint. Standard Paint palette colors are reused instead of being re-entered. Small high-edge colors receive a bounded reserve so eyes, thin contours and isolated color fields are less likely to be lost.

Exact RGB controls are saved as soon as the Edit colors dialog is calibrated. Full canvas detection is a separate gate: if the Paint canvas is clipped or must be selected manually, working RGB calibration is retained. Runtime drawing still verifies rendered color; preloading a picture palette never marks a color as verified by itself.
