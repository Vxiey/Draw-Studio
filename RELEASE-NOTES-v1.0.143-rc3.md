# Draw Studio 1.0.143-rc3

## Microsoft Paint — selected canvas authority

- Fixes the `Paint canvas border is ambiguous or covered. Clear Paint or select the drawing area manually.` failure shown after a drawing area had already been selected.
- **Prepare Paint & draw now honors the existing selected Paint canvas** instead of forcing a second visual border guess.
- The selected canvas is reused only when it still belongs to the same Paint window and the client size is unchanged. If Paint only moved, the selection is safely rebased. If Paint resized or the target changed, Draw Studio falls back to fresh detection.
- Palette/tool/RGB calibration still runs normally, including Edit colors and picture custom palette support.

## Automatic border safety

- Automatic detection keeps the full document envelope so a black/covered region inside the canvas cannot make Draw Studio choose a smaller white sub-area.
- Auto-detected visible borders use a larger inward safety margin to absorb Paint's pale shadow and resize chrome.
- Compact and clipped canvases remain supported. Truly tiny, covered, invalid or out-of-window areas remain blocked.

## Verification

- Full Windows/Linux CI and DrawBot Windows self-test are required before publication.
- The Windows release workflow additionally validates package integrity and a silent install → self-test → uninstall round trip.
