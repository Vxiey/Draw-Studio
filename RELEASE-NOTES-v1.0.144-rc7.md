# Image Draw Bot v1.0.144-rc7 — Save picture colors in Paint

- Custom color palette for picture now presses Paint's + / Add to custom colors for each selected image color. OK alone did not save custom slots.
- Keep Edit colors open for the batch and press OK once at the end.
- Allow at least 750 ms after each Add action; preserve cancellation between colors.
- Identify the Add control and verify the entered RGB values before saving. Stop if controls or values cannot be verified.
- Bound picture-palette preparation to 24 colors for the modern Paint layout shown in the report.

Includes rc5/rc6 calibration and readiness fixes. Automated tests cover sequence, pacing and fail-closed behavior; a real run on the user's Paint version is still needed to confirm slot insertion and crash resolution.
