# Draw Studio 1.0.133-rc2

Check updates now discovers a newer eligible GitHub release, downloads its Windows installer, verifies the published SHA-256 digest and size, and starts the normal installer. Draw Studio saves settings and closes after launch; the installer offers to reopen the app. Installed builds retain their installation directory. Portable/source builds use the normal installation wizard.

Only an explicit Check updates action triggers this flow. Stop cancels pending downloads/installation handoff. Draft releases, older versions, incorrect asset names and unverified installers are rejected. Failed downloads never overwrite the running application. This uses full versioned installers, not binary delta patches.

Includes Extra Fast improvements and automatic Paint RGB preparation from rc1. Paint UI Automation still requires live validation on the user's Paint version.

This first updater-enabled build must be installed once from GitHub Releases. Earlier builds can discover the new version but do not contain the new installer handoff.
