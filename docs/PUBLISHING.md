# Publishing Draw Studio

Draw Studio release publishing is intentionally gated and local-first. The release tools do not upload user runtime data, screenshots, calibration state or diagnostics.

## Source verification

From the repository root:

```powershell
python ReleasePackage.py --check
python ReleaseCandidateHardening.py --source-gate --soak-cycles 5000
python -m unittest discover -v
python DrawBot.py --self-test
```

`ReleasePackage.py` remains the local-only source hygiene/packaging helper. Step 30 adds `ReleaseCandidateHardening.py` as the stricter RC source and Windows-artifact gate.

## Windows build

On Windows x64:

```powershell
python build_release.py --installer
```

This validates source metadata, builds the PyInstaller application, runs the frozen self-test, creates the portable ZIP and Inno Setup installer, generates SHA-256 checksums and writes a release manifest.

## GitHub Actions

`.github/workflows/build-windows.yml` builds when `.github/step30-build-trigger` changes on main, on version tags, or through manual dispatch. For a new release, increment `APP_VERSION`, update matching metadata/tests and release notes, then change the trigger file and push main. A tag build must match `v{APP_VERSION}`.

For RC releases the workflow also performs a silent installer round trip in an isolated temporary directory:

1. silent install,
2. run installed `DrawStudio.exe --self-test`,
3. silent uninstall.

A failure in any gate blocks publication.

## Publishing and updates

After the gates pass, the workflow creates a draft versioned GitHub Release,
uploads the installer, portable ZIP, checksums and manifest, then publishes it.
Published versions are not overwritten. Draft upload retries require the same
commit. Always use a new version number for the next patch.

The in-app updater reads published Releases, not Actions artifacts or branch
commits. It requires the correctly named installer with a GitHub SHA-256 digest.
See [in-app updates](IN-APP-UPDATES.md).

## Signing status

Code signing is not activated. The published rc2 files remain unsigned. Optional
local signing support exists for a future provisioned certificate, but do not
claim signed binaries or Smart App Control compatibility without verification.
Documentation-only changes on main do not replace immutable release downloads.
