# Image Draw Bot v1.0.145-rc26 — Gartic Google Drop-In & Canvas Detection

- Drag images from Google Images, Chrome or Edge directly onto the detected Gartic Phone canvas through Drop-In Start.
- Accept bounded browser `data:image/...;base64` drag payloads in addition to local files, HTTP(S) image URLs and existing Google/Bing redirect handling.
- Improve Gartic Phone canvas detection by ranking multiple plausible regions instead of assuming the largest white component is the canvas.
- Add a conservative Gartic violet-frame/aspect fallback so a partly drawn canvas can still be rediscovered without guessing arbitrary coordinates.
- Keep Browser Auto Calibration edge refinement and CanvasGuard verification authoritative before native drawing input.
- Arm Drop-In Start can discover the Gartic canvas read-only even before palette/setup is complete; the accepted image then goes through Browser One-Click verification before drawing.
- Add global F1 Quick Start. It uses the normal setup guard, temporary unlock and Start flow; Paint continues through Prepare Paint & draw.
- Preserve rc25 Extra Fast regional scheduling, five-brush Gartic execution, Fill safety and preview/execution parity.
- Synchronize installer metadata, current documentation and active regression version assertions to rc26.
