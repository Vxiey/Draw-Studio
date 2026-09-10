# Image Draw Bot v1.0.144-rc11 — Shutdown stability fix

- Fix a Windows shutdown crash where CustomTkinter/Tk could receive a second destroy call after the Tcl application had already been destroyed.
- Make branded root destruction idempotent so converging close/startup-error/teardown paths safely become a no-op after the first shutdown.
- Ignore only the specific TclError that means the application is already destroyed; unrelated Tcl errors still surface normally.
- Install the shutdown guard before optional icon/branding setup so teardown remains protected even if decorative branding cannot load.
- Add regression coverage for the exact "can't invoke destroy command: application has been destroyed" failure and repeated root.destroy() calls.
- Keep the compact UI and all rc10 drawing/rendering behavior unchanged.

The release remains protected by source-package checks, the complete Windows regression suite, ImageDrawBot self-test, packaged-release validation and silent installer install/uninstall verification before publication.
