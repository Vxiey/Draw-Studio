# Image Draw Bot v1.0.144-rc5 — Paint color calibration

- Prevent modal Invoke/Legacy UI Automation calls from blocking the preparation caller until Edit colors closes.
- Reuse an already-open RGB dialog after a previous interrupted calibration instead of attempting to open it again.
- Limit numeric value queries to edit fields and pace readiness scans.
- Include the failed operation in Paint timeout messages.

Control identity checks, cancellation, bounded subprocess timeouts and verification that the dialog closes remain in place. A pending UIA invocation is not treated as proof that RGB controls are ready.

Windows regression coverage includes a blocking-provider helper test and recovery from an already-open color dialog. Compatibility with the user's particular Paint layout still requires a real drawing attempt.
