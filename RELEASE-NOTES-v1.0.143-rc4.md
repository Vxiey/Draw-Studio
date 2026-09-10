# Image Draw Bot 1.0.143-rc4

## Microsoft Paint — Edit colors no longer blocks drawing

- Fixes the startup failure where Image Draw Bot opened **Edit colors** to calibrate or enter RGB values, the modal covered the canvas, and the following canvas verification stopped drawing.
- Automatic Paint preparation now has a hard postcondition: **Edit colors must be closed before canvas verification starts**.
- Image Draw Bot verifies that the RGB controls disappeared from Paint's UI Automation tree instead of assuming that a single Cancel/OK invocation closed the XAML modal.
- If Paint is slow to dismiss the dialog, Image Draw Bot retries only the already identified Cancel/OK control. It never guesses or clicks a canvas coordinate.
- After the modal is gone, Paint is explicitly reactivated and its geometry is re-probed before the canvas/ribbon screenshot is taken.

## Picture custom palette

- Picture-specific RGB preparation now waits for Paint to regain foreground ownership after each confirmed color.
- A lingering Edit colors dialog is explicitly confirmed/closed before the next color or before control returns to Image Draw Bot.
- The picture palette cache behavior is unchanged; only modal lifecycle safety is tightened.

## Verification

- Full Windows/Linux CI and DrawBot Windows self-test are required before publication.
- The Windows release workflow additionally validates package integrity and a silent install → self-test → uninstall round trip.
