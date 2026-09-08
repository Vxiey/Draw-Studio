# Draw Studio

Draw Studio is a Windows desktop drawing automation tool for Microsoft Paint and supported browser drawing apps. The renderer is deterministic: **no AI/ML/OCR models are used**.

## Current beta

**v1.0.124-beta — Step 26: Detail Fidelity, Pixel-Accurate Planning & Named Color Intelligence**

Current verified source package:

- `Draw-Studio-1.0.124-beta-Step26-Color-Engine-Named-Color-Intelligence.zip`
- SHA-256: `34dc39349b544e202166648df972ba2a07519262b425609fe5cd578566d98f49`

Step 26 strengthens full-resolution pixel planning and adds a compatibility/intelligence layer to the Color Engine without expanding or contaminating the calibrated game palette.

### Step 26 highlights

- Full-resolution PixelMap planning
- CPU/GPU-routed pixel and edge analysis
- Improved importance and micro-detail maps
- Better protection for isolated pixels and small features
- Lossless-only simplification safeguards in Pixel Accurate mode
- CSS4 + Tk/X11 named-color compatibility
- Named colors such as `DarkSlateBlue`, `dark slate blue` and normalized aliases
- `#RGB`, `#RGBA`, RGB/RGBA and ARGB parsing support
- `gray` / `grey` alias normalization
- Canonical RGB deduplication for duplicate named colors
- OKLab-based nearest human-readable color naming
- Color-family metadata and improved color diagnostics
- Static lookup tables with no Matplotlib runtime dependency
- Named colors remain metadata/parser inputs and are **not** injected into the drawing quantizer

The Step 24–26 / Color / release regression selection passed **79/79** tests, with an additional **104/104** Advanced Color, Pixel Accurate and DrawBot integration tests passing for this package.

## Download / install

For source use, download the current ZIP above and extract the whole package before running it.

For packaged Windows builds, GitHub Actions can build:

- `DrawStudio-<version>-Windows-x64-Setup.exe` — recommended installer
- `DrawStudio-<version>-Windows-x64.zip` — portable build
- `DrawStudio-<version>-SHA256.txt` — checksums

The packaged EXE does not require Python. Draw Studio runs as the current user and normally should not be run as administrator. Unsigned beta builds may trigger Windows SmartScreen until the project is code-signed.

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
- Full-resolution PixelMap and Pixel Accurate planning
- Detail/importance maps with micro-feature protection
- Named Color Intelligence with CSS4/Tk/X11 compatibility
- OKLab-based color matching and diagnostics
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
