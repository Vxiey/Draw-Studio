# Image Draw Bot 1.0.133-rc3

Fixes a Gartic Phone calibration conflict where Auto Setup could accept a white component extending beyond the visible canvas edge, followed by an execution safety stop.

- Validate detected Gartic bounds with the execution edge verifier before planning; only shrink bounds, never expand them.
- Recalculate cached layouts after upgrading.
- Keep the final edge and mouse guards enabled.
- Add regression coverage for a six-pixel paper extension, clean bounds, screen origins, and oversized manual selections.

The reported logs match the reproduced failure, but the original screen was not included. Live drawing on that exact page still needs confirmation. This release remains unsigned.
