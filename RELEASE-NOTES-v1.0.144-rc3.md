# Image Draw Bot v1.0.144-rc3 — Windows taskbar icon fix

Fix a gap between the Tk window icon and Windows taskbar group identity.

- Set an explicit AppUserModelID, icon, display name and relaunch command on the native app window.
- Use the same bundled ICO directly for Start-menu and desktop shortcuts.
- Reapply the icon when the window is shown again, including after appearance changes.
- Release native window properties before closing and log branding errors.
- Verify taskbar shell properties using the actual app root, including dark-mode changes and hide/show.

The fix covers installed, portable and source launches. Existing pinned shortcuts are managed by Windows; this release does not delete user pins or clear the global icon cache.
