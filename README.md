# Draw Studio – Auto Draw for Gartic Phone, Skribbl.io & Microsoft Paint

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows11&logoColor=white)
![Gartic Phone](https://img.shields.io/badge/Gartic%20Phone-Supported-7C3AED)
![Skribbl.io](https://img.shields.io/badge/Skribbl.io-Supported-2563EB)
![Microsoft Paint](https://img.shields.io/badge/Microsoft%20Paint-Supported-0EA5E9)
![Desktop App](https://img.shields.io/badge/Desktop%20App-CustomTkinter-22C55E)

**Do you suck at drawing but still want to impress your friends?**

**Draw Studio** is a Windows **auto-draw / drawing automation app** that turns images into drawings in **Gartic Phone, Skribbl.io, Microsoft Paint and supported browser drawing apps**. Choose an image, select the canvas, and Draw Studio recreates it with optimized mouse paths, automatic color matching, fills, previews and pixel-accurate detail.

It is built for people who want better-looking drawings without drawing everything by hand, while still keeping full control over speed, accuracy and the target canvas.

> **Gartic Phone:** Google Chrome with the **Artist Tools for Gartic Phone** extension installed and enabled is required for the supported Gartic Phone workflow.
>
> **No AI image generation is used.** Draw Studio analyzes the source image and recreates it through normal mouse drawing, colors, strokes, fills and supported drawing tools.

## What can Draw Studio do?

- Turn an image into an automatic drawing
- Auto-draw in **Gartic Phone, Skribbl.io and Microsoft Paint**
- Draw in supported browser drawing apps
- Match colors automatically
- Preserve small details with Pixel Accurate planning
- Use outlines, strokes, fills and optimized drawing paths
- Create previews before drawing
- Detect and protect the selected canvas area
- Use CPU and GPU acceleration where supported
- Save separate settings for different drawing profiles
- Export/import profiles as portable `.drawprofile` / JSON files
- Stop instantly if something goes wrong

## What is Draw Studio built with?

Draw Studio is mainly written in **Python**. It uses normal desktop automation, image processing and mathematical color analysis rather than an AI model.

### Main technology

- **Python 3.10+** — the main application and drawing/rendering engines
- **Tkinter + CustomTkinter** — the Windows desktop interface
- **Pillow (PIL)** — loading, resizing, converting and analyzing images
- **NumPy** — fast pixel, color, mask and image-array processing
- **OKLab color math** — perceptual color matching and color-difference analysis
- **keyboard** — global controls such as emergency stop/pause hotkeys
- **tkinterdnd2** — drag-and-drop image support
- **requests** — HTTP/HTTPS features that are explicitly requested, such as loading an image URL
- **qrcode** — QR-based/mobile-preview related features

### Optional GPU acceleration

Draw Studio can run without GPU acceleration and fall back to the CPU when needed.

- **NVIDIA:** CuPy/CUDA acceleration can be installed automatically inside Draw Studio's own Python environment. A compatible NVIDIA graphics driver is required, but a separate system-wide CUDA Toolkit is not required for the normal source setup.
- **AMD / Intel / NVIDIA:** PyOpenCL can use the OpenCL runtime supplied by the installed graphics driver for supported workloads and hardware benchmarking.
- If GPU setup fails or is unavailable, Draw Studio keeps a **CPU fallback** instead of requiring a specific GPU.

### Windows packaging and development tools

- **PyInstaller** — creates the packaged Windows application/EXE
- **Inno Setup** — can create a Windows installer when installed on the build machine
- **Batch scripts (.bat)** — startup, diagnostics and local build helpers
- **GitHub Actions (YAML)** — automated Windows builds, testing and release publishing

Draw Studio does **not** depend on AI/ML/OCR models, cloud image processing or a remote rendering server.

## What do I need before first use?

### For the current source ZIP

You need:

- **Windows 10 or Windows 11, 64-bit**
- **Python 3.10 or newer**
- Internet access during the first start so required Python packages can be installed
- Microsoft Paint or a supported browser drawing target
- The **entire ZIP extracted** to a normal writable folder
- Draw Studio and the target application running at the **same privilege level** — normally both should be run without administrator rights

### Gartic Phone requirement

If you want to use Draw Studio with **Gartic Phone**, you also need the Chrome extension **Artist Tools for Gartic Phone** installed and enabled in Google Chrome. Draw Studio's Gartic Phone profile relies on that extension for the supported Gartic drawing workflow.

Make sure the extension is active before starting Gartic Phone and before calibrating or testing the Gartic profile in Draw Studio.

When installing Python, make sure Windows can find Python from the command line. Enabling **Add Python to PATH** during Python installation is recommended.

You do **not** need to manually install every Python package. `Start.bat` creates a private `.venv` environment and installs the dependencies from `requirements.txt` automatically.

### For a packaged EXE build

A packaged `DrawStudio.exe` build does not require a separate Python installation. Extract/install the complete build and start the application normally.

### Before your first real drawing

Have these ready:

1. The image you want to draw.
2. Microsoft Paint or the supported drawing website open.
3. **For Gartic Phone: Google Chrome with Artist Tools for Gartic Phone installed and enabled.**
4. A blank or ready drawing canvas.
5. The target window placed at the size/position you intend to use.
6. The correct Draw Studio profile selected.
7. Color/tool calibration completed when the profile requires it.
8. The drawing area selected correctly.
9. A mouse test, small drawing test and Fast Dry Run completed before the first full drawing.

If you later move, resize, zoom or significantly change the target app, Draw Studio may ask you to verify or redo parts of the calibration.

## Quick Start

### 1. Download Draw Studio

Download the latest Windows ZIP or installer from the repository's **Releases** page.

Current release candidate: **v1.0.130-rc2**

Expected Windows artifacts:

- `DrawStudio-1.0.131-beta-Windows-x64.zip`
- `DrawStudio-1.0.130-rc2-Windows-x64-Setup.exe`

Extract the **entire ZIP** to a normal folder before starting the program, or use the installer build.

Do not run Draw Studio directly from inside the ZIP file.

### 2. Start Draw Studio

If you are running the source version:

```bat
Start.bat
```

On the first launch, Draw Studio:

1. checks for Python 3.10+,
2. creates its local `.venv`,
3. installs/checks the required packages,
4. checks optional GPU acceleration,
5. falls back to CPU if optional GPU acceleration is unavailable,
6. opens Draw Studio.

The first start therefore requires internet access and can do more setup work than later starts.

For packaged Windows builds, launch `DrawStudio.exe` instead.

### 3. Open the app you want Draw Studio to draw in

Microsoft Paint is recommended for your first test.

Open Paint and create a blank canvas.

**Using Gartic Phone?** Open it in Google Chrome and make sure **Artist Tools for Gartic Phone** is installed and enabled before continuing.

### 4. Choose the correct profile

Select the profile that matches the program or drawing website you are using.

Profiles keep their own settings so calibration and renderer settings do not leak into other profiles.

### 5. Add an image

You can load an image by using the image selector, dragging a file into Draw Studio, or pasting an image when supported.

For the best results, use a clear image that is not extremely low resolution.

### 6. Calibrate colors and tools

Some profiles need calibration before the first drawing.

Follow the calibration guide inside Draw Studio. This teaches Draw Studio where the available colors and drawing tools are located.

If you move or resize the target application significantly, recalibration may be required.

### 7. Select the drawing area

Press **Select drawing area** and mark only the part of the target application where drawing is allowed.

This is important. Do not include menus, toolbars, buttons or other UI elements inside the selected drawing area.

### 8. Test before drawing

Before running a full drawing:

1. Run the mouse movement test.
2. Run the small drawing test.
3. Use **Safety preflight**.
4. Run **Fast Dry Run**.
5. Check the preview.

If everything looks correct, unlock full drawing and press **Start drawing**.

## Important controls

- **Esc** — immediately stop drawing
- **F6** — pause or resume drawing

Do not manually move the mouse while Draw Studio is actively drawing unless you stop or pause it first.

## Which drawing mode should I use?

### Fast

Use this when speed matters more than perfect detail.

Good for drawing games with short timers.

### Extra Fast

Designed to finish drawings as quickly as possible by using faster path planning, outlines and fills where appropriate.

Use it when the drawing timer is very short.

### Balanced / normal modes

Best for most images. These modes try to keep a good balance between speed, color accuracy and detail.

### Hybrid Renderer 3.0

Use Auto Hybrid when you want Draw Studio to choose a deterministic specialised renderer for Pixel Art, Icon / Logo, Line Art, Portrait, Shaded Object or Deadline Silhouette. The analysis is local Pillow/NumPy structure analysis — no AI, ML or OCR.

### Pixel Accurate

Use this when preserving the original image is more important than drawing speed.

Pixel Accurate uses full-resolution planning, detail maps and additional safeguards to protect small image features.

It can create significantly more drawing work than faster modes.

## Tips for better drawings

- Start with a reasonably clear source image.
- Crop away unnecessary backgrounds before drawing if the subject is small.
- Make sure the selected drawing area matches the real canvas.
- Use the correct brush width for the target app.
- Calibrate the target palette correctly.
- Check the preview before starting.
- Use faster modes for timed drawing games.
- Use Pixel Accurate when detail matters more than speed.
- Avoid moving or resizing the target window after calibration.
- For Gartic Phone, keep **Artist Tools for Gartic Phone** enabled in Chrome.

## Color Engine

Draw Studio includes an advanced color engine designed to translate source-image colors into colors that the target application can actually draw.

**v1.0.124-beta** introduced **Named Color Intelligence**, including:

- CSS4 and Tk/X11 color-name compatibility
- Names such as `DarkSlateBlue` and `dark slate blue`
- HEX colors such as `#ff0000` and shorthand forms
- RGB, RGBA and ARGB parsing
- `gray` / `grey` alias handling
- Duplicate color-name normalization
- OKLab-based nearest-color analysis
- Human-readable color diagnostics

These extra color names are **not added to the drawing palette automatically**. Draw Studio still uses the palette that was actually calibrated for the selected target application.

## Current release candidate

**v1.0.130-rc2 — Release Candidate Hardening II**

Current Windows release artifact names:

- `DrawStudio-1.0.131-beta-Windows-x64.zip`
- `DrawStudio-1.0.130-rc2-Windows-x64-Setup.exe`
- SHA-256 hashes are generated with the release artifacts

### v1.0.131-beta — Sketch 2.0 + Auto Fill

- **Sketch 2.0 for Microsoft Paint** combines luminance and color-boundary structure so important edges survive even when brightness is similar.
- New **Sketch + Auto Fill** rendering style uses a strict **Sketch → Color Fill → Re-outline** execution order.
- Paint color fill uses safe connected drawing runs after the sketch; the existing bucket-fill prelude is deliberately disabled for this mode so color can never start before the sketch.
- Existing **Adaptive exact/custom RGB** selection is reused when Paint custom-color controls are calibrated.
- Final re-outline restores the strongest structural contours after color fill.
- Gartic Phone, Skribbl.io and other browser execution policies are unchanged.
- Deterministic local image analysis only — no AI, ML or OCR.

### v1.0.130-rc2 — Release Candidate Hardening II

- Removes leftover one-shot integration/patch scripts and workflows from the release branch
- Adds a permanent source-tree hygiene gate that rejects future `*_once.py` and one-shot workflow leakage
- Uses version-only release-note naming for current publishing metadata
- Strengthens manifest validation for app version, file version, channel, architecture, SHA-256 and byte size
- Keeps the RC feature freeze: no renderer or input-safety behavior is loosened
- Retains the verified Windows silent install → installed EXE self-test → silent uninstall gate
- Requires full regression discovery and the 5,000-cycle lifecycle soak before Windows artifacts are accepted

### v1.0.129-rc1 — Release Candidate Hardening

- Release feature set frozen for RC validation
- 5,000-cycle start/stop/disarm lifecycle soak gate
- Repeated profile-storage isolation soak
- Update Center fixed to `Vxiey/Draw-Studio` with RC-aware channel filtering
- Version.py, PE metadata and Inno Setup version consistency gates
- Windows ZIP/installer/SHA-256/manifest validation
- Silent installer → installed EXE self-test → silent uninstall in Windows CI
- Source/release packages reject logs, dumps, bytecode, tests and one-time patch files
- Full regression discovery is a release gate
- Hybrid Renderer 3.0 remains the current renderer; this RC focuses on validation and hardening rather than adding another renderer

### v1.0.128-beta — Hybrid Renderer 3.0

- New **Hybrid Renderer 3.0** rendering style
- **Auto Hybrid** uses bounded local Pillow/NumPy structure analysis — no AI, ML or OCR
- Dedicated **Pixel Art** mode routes into full-resolution Pixel Accurate planning
- **Icon / Logo** uses safe Fill + contour + structural detail passes
- **Line Art** uses contour-first Better Shapes v2 with structural-line preservation
- **Portrait** reuses PortraitPlanner for single-colour targets and high-detail perceptual planning for colour targets
- **Shaded Object** uses progressive base, shade/highlight, contour and detail passes
- **Deadline Silhouette** prioritizes a recognizable subject under short time budgets
- Hybrid policy cannot modify CanvasGuard, target locks, calibration, preflight, dry-run or Start authorization
- Hybrid mode is saved per profile and supported by `.drawprofile` export/import
- Preview diagnostics show requested/resolved Hybrid mode, passes and source-analysis metrics
- Windows regression selection: **64/64 passed**

### v1.0.127-beta — More Drawing Targets

- New dedicated **Kleki** browser-painting profile
- New dedicated **Magma** collaborative-browser profile
- Central `TargetCapabilities` registry for desktop/browser/manual/automatic target semantics
- Verified Browser Auto Setup remains limited to Gartic Phone, Skribbl.io/Fast, SketchHeads and Sketchful.io
- Drawize, Gartic.io, Kleki and Magma intentionally use explicit manual tool/palette/canvas calibration until a current detector is verified
- Automatic browser controls are hidden for manual targets instead of pretending unsupported layouts are safe
- Every target retains isolated settings, palette, tools, layout fingerprint, verified-color cache and timing storage
- No target profile contains native handles, input authorization or hard-coded screen coordinates
- Windows regression selection: **59/59 passed**

### v1.0.126-beta — One-click Setup + Verify

- New **One-click Setup + Verify** action for Microsoft Paint and supported browser drawing games
- Automatically discovers/reuses the target and runs the existing verified canvas/palette setup engine
- Runs a second independent live screenshot verification after initial setup
- Browser verification checks real canvas geometry plus representative saved palette swatches
- Paint verification requires the verified 20-color palette, Pencil + Fill and stable canvas geometry
- Setup never starts drawing and never unlocks mouse/keyboard input
- Failed verification invalidates target/safety readiness and falls back to manual calibration
- Session-only verification state is cleared on every profile switch/reset and is not exported in `.drawprofile`
- Windows regression selection: **41/41 passed**

### v1.0.125-beta — Profile Export / Import

- Export the selected profile as `.drawprofile` or JSON
- Import target, palette/tool calibration, canvas metadata, renderer settings and CPU/GPU/RAM limits
- Schema-versioned format with migration and strict pre-import validation
- Existing-name conflicts support **Replace**, **Import as copy**, or Cancel
- Import-as-copy gets its own isolated `custom-...` storage key
- Reset only the selected profile to defaults
- Hardware benchmark/timing feedback and all native-input authorization are deliberately excluded
- Imported calibration must pass the normal target/safety verification again before drawing

### Security hotfix

- Hardened image-search URL parsing against deceptive Bing/Google hostnames
- Domain checks now use the parsed hostname and real DNS label boundaries
- Added regression tests for hostname spoofing and path/query lookalikes
- GitHub CodeQL alert #2 is confirmed **fixed**

### v1.0.124-beta — Detail Fidelity & Named Color Intelligence

- Full-resolution PixelMap planning
- CPU/GPU-routed pixel and edge analysis
- Improved importance and micro-detail maps
- Better protection for isolated pixels and small features
- Lossless-only simplification safeguards in Pixel Accurate mode
- CSS4 + Tk/X11 named-color compatibility
- Named-color parsing and aliases
- OKLab-based nearest human-readable color naming
- Improved color diagnostics
- Static lookup tables with no Matplotlib runtime dependency
- Named colors remain outside the calibrated drawing quantizer

The v1.0.124-beta Color/Pixel Accurate regression selection passed **79/79** tests, with an additional **104/104** Advanced Color, Pixel Accurate and DrawBot integration tests passing for that package.

## Troubleshooting

### Gartic Phone profile is not working

- Use **Google Chrome**.
- Install and enable **Artist Tools for Gartic Phone**.
- Reload Gartic Phone after enabling the extension.
- Make sure the Gartic Phone profile is selected in Draw Studio.
- Re-run calibration and the drawing-area test after changing the browser layout or zoom.

### The mouse is drawing in the wrong place

- Stop with **Esc**.
- Check that the correct profile is selected.
- Re-select the drawing area.
- Re-run calibration if the target window moved or changed size.
- Run the mouse test again before starting a full drawing.

### Colors are wrong

- Re-run color calibration.
- Make sure the correct profile is selected.
- Check that the target application's palette has not changed.
- Verify the preview before drawing.

### Drawing is too slow

Try:

- Fast or Extra Fast mode
- reducing unnecessary detail
- using a smaller drawing area
- using fills when supported
- lowering extremely aggressive Pixel Accurate settings
- enabling appropriate CPU/GPU resource allocation

### Drawing loses small details

Try:

- Pixel Accurate mode
- Detail Zoom / detail-preservation features
- a larger drawing area
- a smaller brush size
- avoiding overly aggressive speed optimization

### Draw Studio stops or blocks a stroke

This may be the safety system preventing the mouse from drawing outside the selected canvas.

Check the Safety Map / Debug Overlay and make sure the drawing area was selected correctly.

### Python is not found

For the source ZIP, install 64-bit Python 3.10 or newer and enable **Add Python to PATH** during installation. Then run `Start.bat` again.

### First start cannot install packages

Make sure the computer has internet access and that Python/pip is not being blocked by security software or a restricted network. `Start.bat` records startup output in `%TEMP%\DrawStudio-start.log`.

### GPU acceleration is unavailable

GPU acceleration is optional. Update the graphics driver first. If the optional GPU backend still cannot initialize, Draw Studio can continue with its CPU fallback.

### Windows SmartScreen appears

Unsigned beta builds may trigger Windows SmartScreen. This is common for small projects that do not yet use a commercial code-signing certificate.

Only download builds from the official Draw Studio repository.

## Safety architecture

Draw Studio contains multiple independent safety layers designed to keep drawing inside the selected canvas.

These include:

- CanvasGuard
- SafePolygon
- brush inset protection
- safe Fill masks
- segment clipping
- edge verification
- FinalMouseGuard

A drawing profile cannot disable these core protections.

Preview uses the same edge and safety policy as execution.

After Fast Dry Run or real drawing, Draw Studio can write local JSON and TXT safety reports under the app-data `safety-reports` folder.

**Tools → Runtime safety report** can show the latest counters for drawn, clipped, skipped, edge-followed and blocked paths.

## Privacy

Draw Studio is designed to work locally.

- No telemetry
- No automatic crash-report upload
- No remote bug-report backend
- No automatic diagnostics upload
- Source images are not included in diagnostics ZIPs
- Runtime safety reports stay local

Image URLs are the main normal feature that may make an HTTP/HTTPS request when explicitly used by the user.

## Key features

- Automatic image-to-drawing workflow
- Microsoft Paint support
- Supported browser drawing profiles
- Gartic Phone support through **Artist Tools for Gartic Phone** in Chrome
- Profile Engine v2
- Separate settings per profile
- Portable `.drawprofile` / JSON export and import
- Replace / Import as copy conflict handling
- Reset one profile to Draw Studio defaults without changing other profiles
- Canvas Guard and safe drawing boundaries
- Automatic canvas detection and transform/rebase support
- Safe Fill Mask
- Segment-by-segment stroke clipping
- Smart Preview Safety
- Safety Debug Overlay
- Full-resolution PixelMap
- Pixel Accurate planning
- Detail and importance maps
- Micro-feature protection
- Named Color Intelligence
- OKLab-based color analysis
- CPU/GPU/RAM resource scheduling
- Local diagnostics
- First-run guide and tooltips
- No AI/ML/OCR models

## Run from source

Requirements:

- Windows 10 or Windows 11 x64
- Python 3.10 or newer
- Internet access during the first dependency installation
- For Gartic Phone: **Google Chrome + Artist Tools for Gartic Phone**

Run:

```bat
Start.bat
```

`Start.bat` creates `.venv`, installs `requirements.txt`, checks optional GPU backends and opens Draw Studio.

Core source dependencies currently include NumPy, Pillow, Requests, keyboard, tkinterdnd2, CustomTkinter and qrcode. Optional GPU backends are installed only when applicable.

## Build a Windows release locally

Run:

```bat
Build-Release.bat
```

The release builder can:

1. install declared dependencies,
2. run unit tests and source self-tests,
3. build a PyInstaller Windows application,
4. run the packaged self-test,
5. create a portable ZIP,
6. create an Inno Setup installer when available,
7. generate SHA-256 checksums.

Artifacts are written to `release\`.

## GitHub Actions / publisher

The repository uses `.github/workflows/build-windows.yml`.

A manual workflow run can build downloadable Windows artifacts. Pushing a tag that exactly matches the application version can publish a GitHub Release automatically.

## Developer verification

The source-packaging tools are **local-only** and do not upload runtime data.

```powershell
python ReleasePackage.py --check
python ReleaseCandidateHardening.py --source-gate --soak-cycles 5000
python -m unittest discover -v
python DrawBot.py --self-test
```

Legacy internal roadmap documents remain in the repository for development history, but public release notes and README documentation use semantic version numbers.

A public beta should still be tested on a clean Windows 10/11 x64 system with the real target applications before broad release.
