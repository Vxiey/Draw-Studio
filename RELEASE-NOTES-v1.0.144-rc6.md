# Image Draw Bot v1.0.144-rc6 — Picture palette stability

- Calibrate only RGB controls for Custom color palette for picture; do not change Pencil/size as part of this action.
- Wait for identifiable RGB fields before typing, and use their current positions.
- Verify Edit colors has closed before preparing the next color; foreground ownership alone is insufficient.
- Stop the sequence on a readiness failure instead of continuing with keyboard input or subsequent colors.

Includes the rc5 modal UI Automation timeout and interrupted-dialog recovery fixes. These changes address unsafe timing and unnecessary tool preparation. They do not establish the cause of a particular Paint process crash; real Paint-version testing is still needed.
