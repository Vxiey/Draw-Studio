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

`.github/workflows/build-windows.yml` performs the permanent Windows release flow. Tag publication is accepted only when the pushed tag exactly matches `v{APP_VERSION}`.

For RC releases the workflow also performs a silent installer round trip in an isolated temporary directory:

1. silent install,
2. run installed `DrawStudio.exe --self-test`,
3. silent uninstall.

A failure in any gate blocks publication.

## Feature freeze

During the Step 30 RC line, new renderer features are frozen. Publish only blocker/regression/security/installer/update/documentation/test fixes until the stable release is approved.

## Signing

Current binaries are unsigned unless a separate Authenticode signing setup is configured. Do not claim a signed build unless the published artifact was actually signed and verified.
