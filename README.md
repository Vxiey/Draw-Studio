# Draw Studio

Draw Studio is a Windows desktop drawing automation tool for Microsoft Paint and supported browser drawing apps. The renderer is deterministic: **no AI/ML/OCR models are used**.

## Download / install

For normal users, download one of the Windows assets from **GitHub Releases**:

- `DrawStudio-<version>-Windows-x64-Setup.exe` — recommended installer.
- `DrawStudio-<version>-Windows-x64.zip` — portable build. Extract the whole ZIP before launching `DrawStudio.exe`.
- `DrawStudio-<version>-SHA256.txt` — checksums for release files.

The EXE does not require Python. Draw Studio runs as the current user and normally should not be run as administrator. Unsigned beta builds may trigger Windows SmartScreen until the project is code-signed.

## First use

1. Open the target app. Microsoft Paint is recommended for the first test.
2. Start Draw Studio and choose the matching profile.
3. Select, paste or drag in an image.
4. Calibrate colors/tools if the selected profile requires it.
5. **Select drawing area** and select only the drawable canvas.
6. Run the small drawing test.
7. Run **Lock setup → Safety preflight → Fast Dry run**.
8. Check the Drawing preview / Safety map / Debug overlay.
9. Press **Unlock full drawing**, then **Start drawing**.

`Esc` stops immediately. `F6` pauses/resumes. Do not manually move the mouse while a real drawing is running.

## Safety architecture

CanvasGuard, SafePolygon, brush inset, safe Fill masks, segment clipping, edge verification and FinalMouseGuard are intentionally independent from renderer/profile settings. A profile cannot disable them. Preview uses the same edge/safety policy as execution.

### Runtime Safety UI — v1.0.58

After every Fast Dry run or real drawing, Draw Studio writes a local JSON + TXT report under the app-data `safety-reports` folder. **Tools → Runtime safety report** shows the latest counters for drawn, clipped, skipped, edge-followed and blocked paths and can open the report or report folder.

Reports stay local. Draw Studio **does not include telemetry, a bug-report upload server or automatic crash-report sending**. If support is needed, use **Tools → Create diagnostics** and share the generated ZIP manually.

## Key features

- Profile Engine v2 with effective renderer policies
- Manual or profile-controlled rendering policy
- Microsoft Paint and supported browser drawing profiles
- Canvas Guard with safe polygon and brush inset
- Canvas anchor detection and safe transform/rebase
- Deterministic edge verification
- Safe Fill Mask for Better Fill
- Segment-by-segment stroke clipping
- Hard Clip, Adaptive Clip and Preserve Outline edge behaviors
- Smart Preview Safety and Safety Debug Overlay
- Runtime Safety Reports and Runtime Safety UI
- CPU/GPU/RAM resource scheduling
- Local diagnostics without server upload
- First-run guide and hover tooltips
- No AI/ML/OCR models

## Tooltips and guide

Hover important safety controls for a short explanation. **Quick guide** in the header reopens the first-run instructions at any time.

## Run from source

Requirements: Windows 10/11 x64, Python 3.10+ and internet access for first dependency install.

```bat
Start.bat
```

`Start.bat` creates `.venv`, installs `requirements.txt`, and opens Draw Studio.

## Build a Windows release locally

On Windows:

```bat
Build-Release.bat
```

The builder:

1. installs declared dependencies,
2. runs unit tests + source self-test,
3. builds a PyInstaller onedir EXE,
4. runs `DrawStudio.exe --self-test`,
5. creates the portable ZIP,
6. creates an Inno Setup installer when Inno Setup 6 is installed,
7. writes SHA-256 checksums.

Artifacts are written to `release\`.

## GitHub Actions / publisher

The repository uses `.github/workflows/build-windows.yml`. A manual workflow run builds downloadable Windows artifacts. Pushing a tag that exactly matches the app version publishes a GitHub Release automatically.

For v1.0.58-beta:

```powershell
git tag v1.0.58-beta
git push origin v1.0.58-beta
```

The workflow verifies the build on `windows-latest`, creates the installer and portable ZIP, uploads Actions artifacts, and attaches the release assets + checksum to the GitHub Release.

## Privacy

- No telemetry.
- No remote bug-report/reporting backend.
- No automatic diagnostics upload.
- Source images are not included in diagnostics ZIPs.
- Runtime safety reports are local-only.
- Image URLs are the only normal feature that may make an HTTP/HTTPS request when explicitly used by the user.

## Developer verification

```powershell
python -m unittest discover -v
python DrawBot.py --self-test
```

A public beta should still be tested on a clean Windows 10/11 x64 machine with the real target applications before publishing broadly.
