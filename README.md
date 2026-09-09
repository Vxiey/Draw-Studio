# Draw Studio

**Turn images into drawings in Microsoft Paint, Gartic Phone, Skribbl.io and supported drawing apps.**

Draw Studio is a Windows desktop app that recreates images with mouse paths,
color matching, outlines and fills. It uses local image processing, not AI image
generation. Each target profile keeps its own calibration and drawing settings.

## Download — v1.0.142-rc1

| Download | How to use it |
| --- | --- |
| [Windows installer — recommended](https://github.com/Vxiey/Draw-Studio/releases/download/v1.0.142-rc1/DrawStudio-1.0.142-rc1-Windows-x64-Setup.exe) | Run Setup, then open Draw Studio. No separate Python installation needed. |
| [Portable Windows ZIP](https://github.com/Vxiey/Draw-Studio/releases/download/v1.0.142-rc1/DrawStudio-1.0.142-rc1-Windows-x64.zip) | Extract the entire ZIP, open the DrawStudio folder and run DrawStudio.exe. Keep its supporting files together. |
| [SHA-256 checksums](https://github.com/Vxiey/Draw-Studio/releases/download/v1.0.142-rc1/DrawStudio-1.0.142-rc1-SHA256.txt) | Verify the downloaded files. |

[All releases](https://github.com/Vxiey/Draw-Studio/releases) ·
[Release notes](RELEASE-NOTES-v1.0.142-rc1.md) ·
[Documentation](README-INDEX.md)


### Picture custom palette for Microsoft Paint

After loading an image and calibrating Paint, use **Custom color palette for picture** to analyze the current picture, prepare its important exact RGB colors through **Edit colors**, and cache that image-specific palette. The action is Paint-only, bounded and cancel-safe. Exact RGB control calibration is saved independently from canvas detection, so a clipped Paint canvas can still use manual area selection without losing custom-color support.

Requires **Windows 10/11, 64-bit**. Run Draw Studio and the target app at the same
privilege level, normally without administrator rights.

**This release is unsigned.** Windows may display “Unknown publisher” or
SmartScreen warnings, and Smart App Control can block execution. Code signing
has not been activated. Passing build tests does not mean Windows app-control
approval.

## Quick start: Microsoft Paint

1. Open Draw Studio and choose **Microsoft Paint**.
2. Load, paste or drop an image.
3. Keep one Paint window with a blank, fully visible canvas. If no Paint window
   is visible, automatic preparation attempts to open it.
4. Press **Prepare Paint & draw**.

Before drawing, the app selects Pencil and 1 px, detects the canvas and palette,
and opens **Edit colors / Redigera färger** to calibrate the RGB fields and OK
button. It dismisses the dialog after calibration, then uses the fresh controls
for custom colors during drawing.

**No mandatory small test, preview or separate unlock is required for Paint.**
Use **Prepare Paint automatically** to prepare without drawing. Manual
calibration and diagnostic controls remain available.

Automatic preparation currently matches Swedish/English modern Paint controls,
requires RGB mode in the color dialog, and uses the recognized light ribbon
layout. Covered controls, multiple windows, a nonblank/clipped canvas or an
unsupported layout stop preparation rather than guessing. It does not clear,
resize or replace your document. Live end-to-end automation still needs testing
on the user's Paint version. [Paint setup details](docs/PAINT-AUTOMATIC-PREPARATION.md)

## Quick start: drawing games and other apps

1. Open the target and choose the matching Draw Studio profile.
2. Load an image and use that profile's automatic setup or manual calibration.
3. Select only the drawable canvas; keep toolbars and menus outside the area.
4. Choose a drawing mode and time budget.
5. Press **Unlock full drawing**, then **Start Drawing** within 12 seconds.

Previews and small tests are optional diagnostics. Keep the target window,
scaling and browser zoom unchanged after calibration.

**Gartic Phone:** the supported workflow requires Google Chrome with
**Artist Tools for Gartic Phone** installed and enabled.

## Controls

- **Esc:** stop drawing.
- **F6:** pause or resume.
- Stop or pause before manually moving the mouse.

## Updates

Installed Windows builds can press **Check updates / install** while the app is idle. A newer verified release is installed over the same Draw Studio installation and the app relaunches automatically after Setup completes.
It finds a newer eligible GitHub Release, downloads its Windows installer,
verifies the published SHA-256 digest and size, and opens the installer.
Settings are saved and Draw Studio closes after the installer starts.

Installed builds keep their installation folder. Portable/source builds use
the normal installer destination. Updates use complete installers; they do not
apply individual source-code patches. There are no background update checks.

Install rc3 once using the download above if you have an older build. RC builds
accept newer RC/stable releases; stable builds do not automatically switch to
prereleases. [Update details](docs/IN-APP-UPDATES.md)

## Drawing modes and features

| Mode or feature | Purpose |
| --- | --- |
| Extra Fast | Uses safe outline/fill substitutions and connected scanlines to reduce separate drags. |
| Balanced | General-purpose speed and detail settings. |
| Pixel Accurate | Prioritizes small details and source coverage; can take longer. |
| Auto Hybrid | Chooses among specialized deterministic renderers for different image structures. |
| Adaptive Exact colors | Uses calibrated custom RGB controls when the normal palette is not a close enough match. |
| Manual previews | Inspect the planned result without rebuilding a preview after every setting change. |
| Separate profiles | Keep per-target settings and calibration isolated; export/import profiles when needed. |

Extra Fast's six synthetic comparison cases preserved source-raster coverage.
For example, a vertical block went from 280 paths to 3. Actual drawing speed in the target application has not been measured by this benchmark.
[Benchmark and limitations](docs/EXTRA-FAST-REVIEW.md)

## Troubleshooting

- **Automatic Paint setup fails:** expose the whole blank canvas, close menus,
  use RGB mode in Edit colors and check the supported layout described above.
- **Wrong position or colors:** stop, verify the selected profile and recalibrate
  after window, DPI or zoom changes.
- **Too slow:** try Extra Fast, crop unnecessary backgrounds or reduce detail.
  A lower path count does not remove target input and fill delays.
- **No update appears:** only published Releases count, not arbitrary commits or
  Actions artifacts. The current version must be older than the release.
- **Download verification fails:** retry Check updates. A failed download does
  not replace the installed app.
- **Windows blocks the app:** rc3 is unsigned; Smart App Control compatibility
  is not established. The project does not require disabling Windows protection.

## Run from source

Install Python 3.10+ on Windows, extract the complete source and run:

```bat
Start.bat
```

The source launcher creates a private Python environment and installs required
packages; first setup needs internet. Packaged downloads above include Python.
CPU operation is supported. GPU acceleration depends on compatible hardware and
drivers. Optional source-environment installers are `Install-GPU-NVIDIA.bat`
and `Install-GPU-Universal.bat`; normal startup does not automatically install
optional GPU packages.

## Development and release validation

Built with Python, CustomTkinter/Tkinter, Pillow and NumPy; Windows packages use
PyInstaller and Inno Setup.

```powershell
python ReleasePackage.py --check
python -m unittest discover -v
python DrawBot.py --self-test
python ReleaseCandidateHardening.py --source-gate --soak-cycles 5000
python build_release.py --installer
```

You can also use `Build-Release.bat` for the local Windows build.

The rc3 Windows workflow passed tests, packaging and a silent install/self-test/
uninstall round trip. Real drawing speed, GPU behavior and compatibility with
every target layout require separate live testing.

[Publishing](docs/PUBLISHING.md) · [Package layout](docs/RELEASE-STRUCTURE.md) ·
[Version history](VERSION-HISTORY.md)

## Privacy

Image analysis and rendering are local. No telemetry is included. Explicit
features such as checking updates, loading an image URL, source dependency
installation or optional network preview can use the network. The updater uses
public releases from **Vxiey/Draw-Studio**.
