# In-app updates

Press **Check updates / install** while Draw Studio is idle. The installed Windows app checks public GitHub Releases in `Vxiey/Draw-Studio` for the newest version allowed by the current release channel.

For installed builds, Draw Studio downloads only the exact versioned Windows x64 Setup asset, validates the published size and GitHub SHA-256 digest, validates the PE header, hashes the file again immediately before launch, and then starts the installer in the existing installation directory. The app performs its normal controlled shutdown after the installer starts. Setup runs silently for an in-app upgrade and relaunches Draw Studio after replacement completes.

The updater does not use forced process termination. A failed, cancelled, truncated, oversized, redirected-to-an-unexpected-host, or checksum-mismatched download is removed without touching the installed application. The fixed Inno Setup AppId keeps upgrades attached to the same installation.

Portable ZIP and Python-source runs are never silently overwritten in place. They use the normal installer destination/flow instead.

Stable builds do not upgrade to prereleases. RC builds accept newer RC or stable releases. Updates use complete verified installers rather than binary delta patches.

## Publishing future patches

Increment `APP_VERSION`/`FILE_VERSION`, synchronize release metadata/tests, and add the matching release notes. A `Version.py` change merged to `main` automatically triggers the verified Windows release workflow. The workflow runs release hardening, full Windows tests, `DrawBot.py --self-test`, package validation and a silent install/self-test/uninstall round trip before publishing the versioned installer, portable ZIP, SHA-256 file and manifest.

Published versions are not overwritten. Draft upload retries must target the same commit. Release tags must match `APP_VERSION`.

The first updater-enabled release was `1.0.133-rc2`; `1.0.140-rc1` strengthened installed-build in-place update and automatic relaunch behavior. `1.0.143-rc4` is delivered through the same verified update chain.

References: [GitHub release asset digests](https://github.blog/changelog/2025-06-03-releases-now-expose-digests-for-release-assets/) and [Inno Setup command-line parameters](https://jrsoftware.org/ishelp/topic_setupcmdline.htm).
