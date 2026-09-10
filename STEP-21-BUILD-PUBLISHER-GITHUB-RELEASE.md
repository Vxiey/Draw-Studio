# Step 21 — Build / Publisher / GitHub Release Clean-up

This step turns the current beta tree into a cleaner release-ready source package without changing the renderer, color engine, calibration logic or drawing strategy.

## Goals

- Keep the repository root understandable for new users and for GitHub visitors.
- Keep release artifacts deterministic and checksumed.
- Prevent runtime logs, safety reports, crash dumps, build folders and nested release ZIPs from being published accidentally.
- Make the GitHub Actions release flow build from either an unpacked source tree or a source ZIP.
- Keep source release, Windows ZIP, installer and SHA-256 files using one naming convention.

## Release artifact naming

- Source package: `Image-Draw-Bot-<version>-Source.zip`
- Windows portable ZIP: `ImageDrawBot-<version>-Windows-x64.zip`
- Optional CUDA portable ZIP: `ImageDrawBot-<version>-Windows-x64-CUDA.zip`
- Optional installer: `ImageDrawBot-<version>-Windows-x64-Setup.exe`
- Checksums: `ImageDrawBot-<version>-SHA256.txt`
- Manifest: `ImageDrawBot-<version>-ReleaseManifest.json`

## Clean source tree rules

The publisher excludes or blocks:

- `.git`, virtualenvs, build folders, `dist/`, `release/`
- `logs/`, `safety-reports/`, `diagnostics/`, `reports/`
- crash dumps, `.log`, `.tmp`, `.pyc`, `.spec`
- nested generated `Image-Draw-Bot-*.zip` / `ImageDrawBot-*.zip` artifacts

## Local validation

Run:

```powershell
python ReleasePackage.py --check
python ReleasePackage.py --source-zip release\Image-Draw-Bot-1.0.124-beta-Source.zip --manifest release\ImageDrawBot-1.0.124-beta-ReleaseManifest.json
python -m unittest test_step21_release_cleanup_v10144 -v
python DrawBot.py --self-test
```

On Windows, build the EXE package with:

```powershell
Build-Release.bat
```

## GitHub publishing

For a full tagged release:

```powershell
git tag v1.0.124-beta
git push origin v1.0.124-beta
```

The workflow validates the source tree, runs tests, builds the Windows package, creates checksums and publishes the tag release.

## What this step does not change

- No renderer behavior changes.
- No palette matching changes.
- No timing/auto-tuner behavior changes.
- No correction targeting changes.
- No telemetry, network reporting or user-image storage is added.
