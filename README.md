# Draw Studio

**Do you suck at drawing but still want to impress your friends?**

Draw Studio can take an image and automatically recreate it for you in **Microsoft Paint** and supported browser drawing apps. Pick an image, select where it should be drawn, and let Draw Studio handle the lines, colors and details.

It is made for people who want better-looking drawings without having to draw everything by hand.

> **No AI image generation is used.** Draw Studio analyzes the image and recreates it using normal mouse drawing, colors, strokes and supported drawing tools.

## What can Draw Studio do?

- Turn an image into an automatic drawing
- Draw in Microsoft Paint and supported browser drawing apps
- Match colors automatically
- Preserve small details with Pixel Accurate planning
- Use outlines, strokes, fills and optimized drawing paths
- Create previews before drawing
- Detect and protect the selected canvas area
- Use CPU and GPU acceleration where supported
- Save separate settings for different drawing profiles
- Stop instantly if something goes wrong

## Quick Start

### 1. Download Draw Studio

Download the latest ZIP from this repository:

`Draw-Studio-1.0.124-beta-Step26-Color-Engine-Named-Color-Intelligence.zip`

Extract the **entire ZIP** to a normal folder before starting the program.

Do not run Draw Studio directly from inside the ZIP file.

### 2. Start Draw Studio

If you are running the source version:

```bat
Start.bat
```

The first launch may install required Python packages automatically.

For packaged Windows builds, launch `DrawStudio.exe` instead.

### 3. Open the app you want Draw Studio to draw in

Microsoft Paint is recommended for your first test.

Open Paint and create a blank canvas.

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

## Color Engine

Draw Studio includes an advanced color engine designed to translate source-image colors into colors that the target application can actually draw.

Step 26 adds **Named Color Intelligence**, including:

- CSS4 and Tk/X11 color-name compatibility
- Names such as `DarkSlateBlue` and `dark slate blue`
- HEX colors such as `#ff0000` and shorthand forms
- RGB, RGBA and ARGB parsing
- `gray` / `grey` alias handling
- Duplicate color-name normalization
- OKLab-based nearest-color analysis
- Human-readable color diagnostics

These extra color names are **not added to the drawing palette automatically**. Draw Studio still uses the palette that was actually calibrated for the selected target application.

## Current beta

**v1.0.124-beta — Step 26: Detail Fidelity, Pixel-Accurate Planning & Named Color Intelligence**

Current verified source package:

- `Draw-Studio-1.0.124-beta-Step26-Color-Engine-Named-Color-Intelligence.zip`
- SHA-256: `34dc39349b544e202166648df972ba2a07519262b425609fe5cd578566d98f49`

### Step 26 highlights

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

The Step 24–26 / Color / release regression selection passed **79/79** tests, with an additional **104/104** Advanced Color, Pixel Accurate and DrawBot integration tests passing for this package.

## Troubleshooting

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
- Profile Engine v2
- Separate settings per profile
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

Run:

```bat
Start.bat
```

`Start.bat` creates `.venv`, installs `requirements.txt`, and opens Draw Studio.

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

```powershell
python -m unittest discover -v
python DrawBot.py --self-test
```

A public beta should still be tested on a clean Windows 10/11 x64 system with the real target applications before broad release.
