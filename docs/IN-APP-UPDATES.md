# In-app updates

Press **Check updates / install** while idle. Draw Studio checks public GitHub
Releases in Vxiey/Draw-Studio for a newer version allowed by the current release
channel. It downloads the release's exact Windows x64 Setup asset, verifies its
published size and GitHub SHA-256 digest, then opens the normal installer.
Settings are saved before handoff. Draw Studio closes only after the installer
process has started successfully. The installer offers to launch the updated app.

Installed builds pass their existing installation directory to the installer.
Portable and Python-source builds use the normal installer destination. Updates
use full installers, not binary delta patches. Windows may show its normal
security/installer prompts. No background timer checks or downloads are added.

Stop cancels download or pending handoff. Failed or mismatched downloads are
removed without touching the installed application. The file is hashed again
immediately before launch. Only assets belonging to the exact version and
repository with a published SHA-256 digest qualify for automatic installation.
Missing installers produce a retry/Releases message instead of executing a ZIP
or unverified EXE. Stable builds do not upgrade to prereleases; RC builds accept
newer RC or stable releases.

## Publishing future patches

Increment APP_VERSION (and update release metadata/tests/notes), then change
.github/step30-build-trigger and push main. The workflow builds and tests Windows,
checks installation/uninstallation, uploads artifacts and publishes a versioned
GitHub Release. The release stays draft until all assets upload successfully.
Published versions are not overwritten. Draft upload retries require the same
commit. Tags must match APP_VERSION.

The first updater-enabled release is 1.0.133-rc2. Install it once from Releases;
earlier builds do not contain the new download/installer handoff. Subsequent
newer releases are found from inside the application.

References: [GitHub release asset digests](https://github.blog/changelog/2025-06-03-releases-now-expose-digests-for-release-assets/)
and [Inno Setup command-line parameters](https://jrsoftware.org/ishelp/topic_setupcmdline.htm).
