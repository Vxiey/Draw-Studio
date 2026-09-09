v1.0.131-beta Sketch 2.0 + Auto Fill improves Paint sketch structure with color-boundary edges and adds a strict Sketch -> Color Fill -> Re-outline renderer that reuses calibrated custom RGB while leaving browser/Gartic execution unchanged.
v1.0.130-rc2 Release Candidate Hardening II removes leftover one-shot integration files, adds permanent source-tree hygiene enforcement, adopts version-only current release-note naming, and strengthens release-manifest version/channel/hash/size validation while keeping the RC feature freeze.

v1.0.129-rc1 Step 30: Release Candidate Hardening freezes the numbered feature roadmap, adds executable source/artifact release gates, 5,000-cycle lifecycle and profile-isolation soak checks, fixes Update Center repository/channel handling, validates Windows ZIP/installer/checksums/manifests, and requires a silent install/self-test/uninstall round trip before RC publication.
v1.0.128-beta Step 29: Hybrid Renderer 3.0 adds deterministic Auto Hybrid plus Pixel Art, Icon / Logo, Line Art, Portrait, Shaded Object and Deadline Silhouette modes; it reuses the existing Pixel Accurate, Quick Sketch, Shape Paths and PortraitPlanner engines while preserving CanvasGuard, calibration and profile isolation.
v1.0.127-beta Step 28: More Drawing Targets adds the TargetCapabilities registry plus isolated Kleki and Magma profiles; unverified browser targets remain manual by design and cannot inherit verified auto-setup semantics.
v1.0.124-beta Step 21: Build / Publisher / GitHub Release Clean-up adds deterministic source release validation, clean source ZIP creation, release manifests, GitHub release template, publishing docs and stronger checks that logs/safety reports/build artifacts are not accidentally shipped.
v1.0.124-beta Step 19/20: Final Profile Polish + Beginner Setup Wizard centralizes Paint/Gartic/Skribbl release presets, target-specific warnings/calibration flows, clearer Start-blocking status, setup wizard dialog and friendlier recovery/error actions.
v1.0.123-beta: Adaptive Palette Fidelity & Anti-Posterization Engine replaces fixed browser 4/6/8-colour reduction with fidelity/deadline-aware palette capacity, tone/hue/spatial anchors, visual-gain-per-switch selection, palette coverage and posterization diagnostics.
v1.0.122-beta: Exact Color Engine + Paint Color Verification adds CIEDE2000-based Faithful/Exact matching, source-backed color representatives, stronger bright-tone protection, Paint exact-RGB recovery after palette mismatches, per-profile verified color caching, and richer preview color diagnostics.
v1.0.121-beta: Direct Game Canvas Web Drop adds a canvas-only 60-second drop target for supported browser games, accepts Google Images/Chrome/Edge file+URL+HTML drag payloads, unwraps Google imgres links, and uses the dropped image as one-shot authorization for Browser One-Click verification and automatic drawing start.
v1.0.120-beta: Color Fidelity & Preview Tone Fix adds sRGB/Lab-aware palette matching, Faithful lightness/saturation preservation, bright-anchor retention in game turbo palettes, GPU parity and removes the artificial 0.68 Fill Preview darkening.
v1.0.119-beta: Deadline Reliability & Runtime Optimizer fixes safety reserves for legacy timers, adds conservative cold-start timing, typed-operation runtime learning, Normal/Catch-up/Panic scheduling, workload-aware CPU workers, verified GPU diagnostics, smarter browser candidate ranking, Start Drawing state tracking, structural-coverage gating and fill value-per-error scoring.
v1.0.118-beta: Adaptive Deadline Renderer adds named Gartic/Skribbl time presets, safety reserves, visual-importance budgeting, progressive deadline-aware scheduling, Panic Mode, local timing calibration and weighted preview accuracy metrics.
v1.0.117-beta: Region Fill Engine adds connected-region planning, conservative outline+fill substitution, leak-risk/cost analysis, stroke fallback, and locally learned draw-time calibration based on completed real drawings.
v1.0.116-beta: 4K + Automatic DPI Recognition Fix centralizes per-monitor DPI detection, adds monitor/system fallbacks, logs effective monitor/DPI metadata, and maps plausible high-DPI selection mismatches back to physical pixels.
v1.0.115-beta: High-DPI Browser Auto Setup Fix scans oversized browser palette ROIs in bounded overlapping tiles, preserving the 1M-pixel per-scan safety limit while supporting 144-DPI/4K Gartic layouts.
v1.0.114-beta: Automatic Canvas Clear adds an opt-in full-draw prelude: Paint Select All/Delete, calibrated browser Clear control, or CanvasGuard-bounded Eraser sweep with Brush restore. Small Test/Dry Run/resume remain protected.
v1.0.113-beta: Detail-Aware Preview adds adaptive oversampled preview resampling, edge-priority micro-detail recovery, and Fast/Balanced/Detailed/Micro detail controls so eyes, pupils and thin contours survive preview downscaling more reliably.
v1.0.112-beta: Contour & Detailed Shadow Rendering adds local shadow analysis, palette-aware contour detection, detailed-shadow protection and post-processing priority while preserving the lossless PixelMap.
v1.0.111-beta: Smart Drop-In Canvas Targeting (EXPERIMENTAL / very early stage) can detect a supported browser game canvas and open a temporary drag/drop overlay; drops outside the drawable canvas are rejected and the normal CanvasGuard/One-Click safety chain remains mandatory.
v1.0.110-beta: Preview Draw Time Estimate shows an estimated final drawing duration directly after Build preview, including projected range when safe preview is smaller than the target canvas.
v1.0.109-beta: Advanced Color Matching measures source mean/median/dominant RGB, prefers exact numeric Paint RGB entry, verifies the selected-color preview, and falls back safely instead of confirming a known-wrong custom color.
v1.0.108-beta: Fix Paint color verification and enable spectrum-only custom palette selection during real drawing.
v1.0.107-beta: Reset all drawing settings before profile load; show only matching Paint/Gartic/browser controls.

v1.0.106-beta: Verified modern Paint automatic canvas, palette and Pencil/Fill setup.

v1.0.105-beta: Extra fast preset uses cost-selected closed contours and bucket fills, with stroke fallback.

v1.0.104-beta: Native-resolution preview, bounded viewport zoom, visible-tab rendering and actual planned colour map.

v1.0.103-beta: Human mode removed from UI; application always plans with it Off.

v1.0.102-beta: Clear image/cache, full Gartic setup, Auto engine and Masterpiece/Unlimited.

v1.0.101-beta: Visual Gartic pie timer observation and conservative drawing deadline.

v1.0.100-beta: Auto sketch detail using configured time budget.

v1.0.99-beta: Adjustable sketch detail, Simple default.

v1.0.98-beta: Gartic connected contour engine.

v1.0.97-beta: Single-color sketch for games, including Gartic.

v1.0.96-beta: sketch/subject-focus conflict no longer blocks drawing.

# Draw Studio Version History

This file is the quick answer to “what changed?” for each beta/source ZIP. It is shipped in the source package and bundled into the Windows build from v1.0.68 onward.

## Current release

| Version | Name | What changed |
|---|---|---|
| 1.0.126-beta Step 27.5 | One-click Setup + Automatic Canvas/Palette Verification | Unified Paint/browser setup, second live canvas/palette verification, fail-closed confidence checks and no drawing authorization. |
| 1.0.124-beta Step 24 | Adaptive Detail Zoom Pass | Re-analyzes bounded source ROIs at 2x/4x, restores palette-safe micro details, adds a Detail zoom preview, and keeps all target-app zoom/calibration coordinates unchanged. |
| 1.0.124-beta Step 19/20 | Profile Polish + Beginner Setup Wizard | Centralizes release presets for Paint/Gartic/Skribbl, applies game time presets in Auto mode, shows what blocks Start, and adds a full setup wizard with target warnings. |
| 1.0.124-beta | Paint Color Selection Recovery & Exact Swatch Verification | Fixes Paint palette→exact recovery, adds optional Active Color 1 swatch verification before strokes, and expands Faithful custom-RGB use for poor palette matches. |
| 1.0.123-beta | Adaptive Palette Fidelity & Anti-Posterization Engine | Replaces fixed 4/6/8-colour browser reduction with adaptive Faithful palette capacity, tone/hue/spatial anchors, weighted DeltaE2000 coverage, midtone protection and posterization diagnostics. |
| 1.0.122-beta | Exact Color Engine + Paint Color Verification | CIEDE2000 palette fidelity, source-backed representative colors, stronger lightness protection, Paint custom-RGB verification/recovery, verified color cache and richer preview color diagnostics. |
| 1.0.121-beta | Direct Game Canvas Web Drop | Drag a Google/Chrome/Edge image directly onto the detected game canvas; file/URL/HTML payloads are normalized, the canvas/palette is re-verified, then the drawing starts automatically through the existing safe browser pipeline. |
| 1.0.120-beta | Color Fidelity & Preview Tone Fix | Faithful sRGB/Lab palette matching, lightness/saturation preservation, bright turbo anchors, GPU fidelity parity and neutral preview tone. |
| 1.0.119-beta | Deadline Reliability & Runtime Optimizer | Fixes automatic timer reserve, conservative cold-start timing, typed-operation learning, Normal/Catch-up/Panic scheduling, workload-aware CPU/GPU diagnostics, browser candidate ranking, Start Drawing state tracking and deadline-aware Region Fill value scoring. |
| 1.0.118-beta | Adaptive Deadline Renderer | Adds real game-time budgets, importance-weighted plan reduction, progressive deadline scheduling, Panic Mode and locally calibrated estimated-vs-actual timing. |
| 1.0.117-beta | Region Fill Engine | Adds connected-region outline+fill planning with hard fill safety gates, cost-based fallback and locally learned final draw-time calibration from completed drawings. |
| 1.0.116-beta | 4K + Automatic DPI Recognition Fix | Centralized automatic target DPI detection, stronger per-monitor awareness, 4K/high-scaling coordinate mapping, monitor diagnostics and safe physical-pixel selection fallback. |
| 1.0.115-beta | High-DPI Browser Auto Setup Fix | Keeps browser palette scanning bounded while supporting oversized 144-DPI/4K palette ROIs. |
| 1.0.114-beta | Automatic Canvas Clear | Opt-in pre-draw clear using Paint shortcut, anchored Clear control, or guarded Eraser sweep; never destroys Small Test/Dry Run/resume state. |
| 1.0.113-beta | Detail-Aware Preview | Preserves eyes, pupils, thin contours, fine facial lines and tiny shadow edges in bounded UI previews using deterministic oversampling and micro-detail recovery. |
| 1.0.112-beta | Contour & Detailed Shadow Rendering | Adds local shadow analysis, contour maps, detailed-shadow protection and post-processing priority while preserving the lossless PixelMap. |
| 1.0.111-beta | Smart Drop-In Canvas Targeting | Experimental early-stage drop-on-canvas targeting for supported browser drawing games with safety fallback. |
| 1.0.110-beta | Preview Draw Time Estimate | Shows projected final drawing time after Build preview. |
| 1.0.109-beta | Advanced Color Matching | Measures real source RGB statistics, enters image-derived R/G/B automatically in Paint, verifies the custom-color preview before OK, and uses spectrum/palette fallbacks when needed. |
| 1.0.96-beta | Sketch start fix | Sketch takes priority over conflicting subject focus; GUI prevents this conflict. |
| 1.0.95-beta | Black contour sketch | Simple black-only contour planner; smoothing, edge thinning, speck removal and no colour fills. |
| 1.0.94-beta | Restore original UI | Restores the v1.0.91 layout/theme and preview tabs; keeps update actions, calibration hiding, startup fix and scroll handling. |
| 1.0.93-beta | Startup hotfix | Fixes undefined release_page_btn reference during UI creation and adds UI name-binding regression check. |
| 1.0.92-beta | Compact workspace | Section navigation, preview selector, wrapped tools, pointer-local scrolling, GitHub update actions and automatic hiding during calibration. |
| 1.0.91-beta | Unified release | Adaptive Brush Draw Motor merged with review/crash diagnostics, Subject Focus, image format detection and upscaling. |
| 1.0.90-beta (Adaptive Brush branch) | Adaptive brush motor | Per-path brush widths, verified browser switching and brush-aware CPU/CUDA simulation; merged into 1.0.91. |
| 1.0.90-beta | Review and crash diagnostics | Correct Windows dump setup, reliable mouse probe output, fill correction scope, order-preserving checkpoints and bounded CUDA launch work. |
| 1.0.89-beta | Pixel Accurate Planner — Block D | CUDA planned-stroke simulation and score reduction, VRAM-aware tiles/batches, parallel CPU region processing, protected progressive time budgets and phase accuracy checkpoints. |
| 1.0.88-beta | Pixel Accurate Planner — Block C | Brush-aware coverage map, executable stroke simulation, categorical pixel error map, improvement-gated correction passes, and measurable pixel/coverage/edge/protected-feature accuracy scores. |
| 1.0.87-beta | Pixel Accurate Planner — Block B | Exact 4-connected regions, local H/V lossless runs, component-safe merge + coverage verification, CPU component scheduling, and four-pass fill/mid/fine/cleanup execution. |
| 1.0.86-beta | Pixel Accurate Planner — Block A | Full fitted-resolution PixelMap, CUDA palette + Sobel analysis, perceptual palette mapping, importance/tiny-feature protection, and quality-first bypass of destructive browser turbo/simplification. |
| 1.0.85-rc1 | Automatic NVIDIA CUDA setup | Start.bat now detects NVIDIA hardware, automatically installs/repairs the CuPy + matched CUDA runtime inside .venv, removes conflicting CuPy families, validates a real CUDA kernel, and keeps CPU fallback if setup fails. |
| 1.0.84-rc1 | Browser palette guard hotfix | Prevent browser drawing from being falsely blocked by Paint palette validation; expose NVIDIA benchmark in GPU settings and show effective planner backend. |
| 1.0.83-rc3 | NVIDIA discovery + canvas drop-to-draw | Detect NVIDIA hardware independently of CuPy, auto-prepare CUDA on NVIDIA systems, real CUDA smoke/benchmark diagnostics, and direct preview-canvas drop-to-draw when setup is ready. |
| 1.0.82-rc2 | RC1 field-log fixes | Gartic conservative-edge handling, CTk scroll guard, Stop log-spam fix and One-Click callback recovery. |
| 1.0.81-rc1 | Stability / Release Candidate | No major renderer features: stress/race cleanup, guaranteed mouse release/disarm, stale callback/worker containment, and settings/cache migration validation. |

## Recent releases

| Version | Name | What changed |
|---|---|---|
| 1.0.80-beta | Browser One-Click Mode | Choose a supported browser game and add an image; Draw Studio discovers/reuses the game window, auto-detects canvas/palette, runs auto brush + visual preflight, then starts without manual calibration. |
| 1.0.79-beta | Smart Recovery / Resume | Saves active color + exact unfinished path on recoverable browser stops; next explicit Start recalibrates/preflights and resumes without redrawing completed paths. |
| 1.0.78-beta | Stroke Delivery Verification | Verifies browser strokes after delivery and retries only a suspected missed/partial stroke once with safer spacing. |
| 1.0.77-beta | Real-Speed Time Budget | Learns completed browser paths/second and adapts 30/60/90-second path, color and detail budgets while prioritizing large outlines/forms. |
| 1.0.76-beta | Layout Fingerprint v2 | Caches browser canvas/palette geometry, client size, DPI and zoom/reflow signatures for near-instant repeated Auto Setup. |
| 1.0.75-beta | Per-Game Input Engine | Separate Gartic/Skribbl/SketchHeads interpolation, stroke spacing, press/release timing and palette-click delays; includes v1.0.74 Automatic Brush Size. |
| 1.0.74-beta | Automatic Brush Size | Auto-detects and safely selects browser brush-size presets for Gartic Phone, Skribbl and SketchHeads; low-confidence layouts use a conservative no-click fallback. |
| 1.0.73-beta | Drop-In Synchronization | Queues a manually armed browser image while Auto Setup/Recalibration/Visual Preflight is running, resumes automatically, keeps only the latest image and cancels on target/profile change. |
| 1.0.72-beta | Browser Visual Preflight | Verifies the visible canvas and representative palette swatches immediately before every browser drawing; retries Auto-Recalibration once and blocks persistent visual mismatches before mouse input. |
| 1.0.71-beta | Browser Auto-Recalibration | Read-only pre-input rescans automatically refresh browser canvas/palette after Chrome zoom, resize, window movement or DPI changes. |
| 1.0.70-beta | Browser Auto Calibration | Auto-detects/anchors browser palettes and safe canvases for Gartic Phone, Skribbl and SketchHeads; manual calibration becomes fallback-only. |
| 1.0.124-beta Step 25 | Quick Sketch Fill + Contour | Adds a recognition-first short-round renderer using verified closed-region OUTLINE_FILL, simplified visible contours, connected scanline fallback and Auto Tuner selection. |
| 1.0.124-beta Step 24 | Adaptive Detail Zoom Pass | Re-analyzes high-value source regions internally at 2x/4x, recovers bounded micro-details and never changes target-app/browser zoom or calibration geometry. |
| 1.0.124-beta Step 23 | Universal GPU Acceleration Engine | Routes real OKLab, palette, DeltaE, quantization, edge and pixel workloads through the fastest Step-22-measured CUDA/OpenCL/CPU backend with per-workload fallback. |
| 1.0.124-beta Step 22 | Universal Hardware Auto Benchmark | Adds NVIDIA/AMD/Intel detection, CUDA/OpenCL/CPU microbenchmarks, per-workload backend selection and a local per-machine adaptive hardware profile. |
| 1.0.69-beta | Mobile Preview Live | Adds an opt-in local Wi-Fi/LAN preview page with Original, Drawing Preview, Safety Map, live refresh and QR/address sharing. |
| 1.0.68-beta | Version History & README Index | Adds VERSION-HISTORY, README-INDEX, docs indexes and an in-app Version history viewer. |
| 1.0.67-beta | Manual Drop-In Start | One-shot browser/game workflow that starts drawing after the next image import when manually armed. |
| 1.0.66-beta | Gartic Engine v2 | Dedicated Gartic layout validation, 72-color palette support, StrokeGraph travel optimization and timer-aware runtime settings. |
| 1.0.65-beta | Gartic Phone Turbo Renderer | Fast Gartic renderer with color batching, horizontal/vertical run selection and fixed-palette drawing. |
| 1.0.64-beta | Skribbl Turbo Renderer | Skribbl.io Fast uses palette reduction, color batching and continuous raster-run compression. |
| 1.0.63-beta | Adaptive Stroke & Input Ownership Fix | Rolls back overly aggressive Paint delivery defaults and reduces false manual-mouse stops. |
| 1.0.62-beta | Paint Stroke Delivery Fix | Adds denser Paint drag delivery and timing fixes for missing mouse-down segments. |
| 1.0.61-beta | Fast Dry Run Completion Fix | Clean Fast Dry Run budget expiry is treated as pass rather than a hard timeout error. |
| 1.0.60-beta | Performance Auto Tuner | Local benchmark for CPU workers, RAM budget, GPU/VRAM policy and planning resolution. |
| 1.0.59-beta | GitHub Update Center | Manual update checker for GitHub Releases with no background checks or automatic downloads. |
| 1.0.58-beta | Runtime Safety UI + Release Prep | Visible runtime safety counters, release packaging and local-only diagnostics cleanup. |

## Earlier development history

These entries are generated from the historical markdown notes in `docs/history/`.

| Version | Note | File |
|---|---|---|
| 1.0.57 | v1.0.57-beta – Runtime Safety Report Step 11 | `docs/history/RUNTIME-SAFETY-REPORT-v1.0.57.md` |
| 1.0.56 | v1.0.56-beta – Safety Debug Overlay Step 10 | `docs/history/SAFETY-DEBUG-OVERLAY-v1.0.56.md` |
| 1.0.55 | v1.0.55-beta – Smart Preview Safety Step 9 | `docs/history/SMART-PREVIEW-SAFETY-v1.0.55.md` |
| 1.0.54 | v1.0.54-beta – Edge Behavior Step 8 | `docs/history/EDGE-BEHAVIOR-v1.0.54.md` |
| 1.0.53 | v1.0.53-beta – Stroke Clip Step 7 | `docs/history/STROKE-CLIP-v1.0.53.md` |
| 1.0.52 | v1.0.52-beta – Safe Fill Mask Step 6 | `docs/history/SAFE-FILL-MASK-v1.0.52.md` |
| 1.0.51 | Draw Studio v1.0.51-beta – Edge Detection Step 5 | `docs/history/CANVAS-EDGE-DETECTION-v1.0.51.md` |
| 1.0.50 | v1.0.50-beta — Anchor Transform Step 4 | `docs/history/ANCHOR-TRANSFORM-v1.0.50.md` |
| 1.0.49 | Canvas Anchor Detection — v1.0.49 | `docs/history/CANVAS-ANCHORS-v1.0.49.md` |
| 1.0.48 | Canvas Polygon — v1.0.48 | `docs/history/CANVAS-POLYGON-v1.0.48.md` |
| 1.0.47 | Canvas Guard — v1.0.47 | `docs/history/CANVAS-GUARD-v1.0.47.md` |
| 1.0.46 | Fast Calibrated Dry Run — v1.0.46 | `docs/history/FAST-DRY-RUN-v1.0.46.md` |
| 1.0.45 | Profile Engine v2 — v1.0.45 | `docs/history/PROFILE-ENGINE-v1.0.45.md` |
| 1.0.44 | Resource Scheduler v2 — v1.0.44 | `docs/history/RESOURCE-SCHEDULER-v1.0.44.md` |
| 1.0.43 | Visual Verification — v1.0.43 | `docs/history/VISUAL-VERIFICATION-v1.0.43.md` |
| 1.0.42 | Render Resume + Color Checkpoints — v1.0.42 | `docs/history/RENDER-RESUME-v1.0.42.md` |
| 1.0.41 | Color Engine v3 — v1.0.41 | `docs/history/COLOR-ENGINE-v1.0.41.md` |
| 1.0.40 | Auto Paint Calibration — v1.0.40 | `docs/history/AUTO-PAINT-CALIBRATION-v1.0.40.md` |
| 1.0.39 | Better Fill Engine v1.0.39 | `docs/history/BETTER-FILL-v1.0.39.md` |
| 1.0.38 | Adaptive Detail Engine — v1.0.38-beta | `docs/history/ADAPTIVE-DETAIL-v1.0.38.md` |
| 1.0.37 | Draw Studio v1.0.37-beta – Smart Stroke Optimizer | `docs/history/STROKE-OPTIMIZER-v1.0.37.md` |
| 1.0.35 | Draw Studio v1.0.35-beta – Adaptive Color Verification + Auto-Recovery | `docs/history/ADAPTIVE-COLOR-v1.0.35.md` |
| 1.0.34 | Draw Studio v1.0.34-beta – Smart Custom Palette + Color Batching | `docs/history/CUSTOM-PALETTE-v1.0.34.md` |
| 1.0.33 | Draw Studio v1.0.33-beta – Color Engine v2 | `docs/history/COLOR-ENGINE-v1.0.33.md` |
| 1.0.32 | Draw Studio v1.0.32-beta — Paint Pencil / opacity safety | `docs/history/PAINT-PENCIL-OPACITY-FIX-v1.0.32.md` |
| 1.0.31 | Draw Studio v1.0.31-beta — Color Calibration Stability | `docs/history/COLOR-CALIBRATION-STABILITY-v1.0.31.md` |
| 1.0.30 | Draw Studio v1.0.30-beta — Preview Stability Fix | `docs/history/PREVIEW-STABILITY-v1.0.30.md` |
| 1.0.29 | Draw Studio v1.0.29-beta — Step 11 UI Icons + Profile Experience | `docs/history/UI-PROFILES-v1.0.29.md` |
| 1.0.28 | Draw Studio v1.0.28-beta — Step 10 Safe Recovery + Diagnostics | `docs/history/SAFE-RECOVERY-DIAGNOSTICS-v1.0.28.md` |
| 1.0.27 | Draw Studio v1.0.27-beta — Step 9 Performance Profiler + Benchmark | `docs/history/PERFORMANCE-PROFILER-v1.0.27.md` |
| 1.0.26 | Draw Studio v1.0.26-beta — Step 8: Renderer v2 / Better Shapes | `docs/history/BETTER-SHAPES-v1.0.26.md` |
| 1.0.25 | Draw Studio v1.0.25-beta — Step 7: Live Target Monitoring | `docs/history/LIVE-TARGET-MONITORING-v1.0.25.md` |
| 1.0.24 | Draw Studio v1.0.24-beta — Step 6: Target Lock + Calibration Fingerprint | `docs/history/TARGET-LOCK-v1.0.24.md` |
| 1.0.23 | Draw Studio v1.0.23-beta — Step 5: Dry Run / No-click Plan Test | `docs/history/DRY-RUN-v1.0.23.md` |
| 1.0.22 | Draw Studio v1.0.22-beta — Step 4: Planning Watchdog + Fallback | `docs/history/PLANNING-WATCHDOG-v1.0.22.md` |
| 1.0.21 | Draw Studio v1.0.21-beta — Step 3: Progressive Renderer | `docs/history/PROGRESSIVE-RENDERER-v1.0.21.md` |
| 1.0.20 | Draw Studio v1.0.20 beta — Step 2: Time Budget + Target Stroke Count | `docs/history/TIME-BUDGET-TARGET-STROKES-v1.0.20.md` |
| 1.0.19 | Draw Studio v1.0.19 beta — Step 1: Preflight Lock | `docs/history/PREFLIGHT-LOCK-v1.0.19.md` |
| 1.0.18 | Draw Studio v1.0.18-beta — Start Failsafe | `docs/history/START-FAILSAFE-v1.0.18.md` |
| 1.0.17 | Draw Studio v1.0.17 beta – Skribbl Fast Renderer | `docs/history/SKRIBBL-FAST-RENDERER-v1.0.17.md` |
| 1.0.16 | Draw Studio v1.0.16 beta – Manual Preview and Start Guard | `docs/history/PREVIEW-START-SAFETY-v1.0.16.md` |
| 1.0.15 | Draw Studio v1.0.15 – Drawing Start Diagnostics | `docs/history/DRAW-START-DIAGNOSTICS-v1.0.15.md` |
| 1.0.14 | Draw Studio v1.0.14 – Real CPU/GPU/RAM Workload Allocation | `docs/history/RESOURCE-ALLOCATION-v1.0.14.md` |
| 1.0.13 | Draw Studio v1.0.13 — CPU / GPU / RAM Allocation | `docs/history/RESOURCE-ALLOCATION-v1.0.13.md` |
| 1.0.12 | Draw Studio v1.0.12 — Smart Continuous Paths | `docs/history/SMART-PATHS-v1.0.12.md` |
| 1.0.11 | Draw Studio v1.0.11 — Manual Preview + Stability Defaults | `docs/history/MANUAL-PREVIEW-PERFORMANCE-v1.0.11.md` |
| 1.0.10 | Draw Studio v1.0.11 — Preview Planning Fix | `docs/history/PREVIEW-PLANNING-v1.0.10.md` |
| 1.0.9 | Draw Studio 1.0.9 beta — Modern UI / UX Redesign | `docs/history/MODERN-UI-v1.0.9.md` |
| 1.0.8 | Draw Studio v1.0.8 — Advanced Color Rendering | `docs/history/ADVANCED-COLOR-v1.0.8.md` |
| 1.0.7 | Draw Studio v1.0.7 — Auto Fill + Smart Tool Control | `docs/history/AUTO-FILL-SMART-TOOLS-v1.0.7.md` |
| 1.0.6 | Draw Studio v1.0.6 — GPU Acceleration | `docs/history/GPU-ACCELERATION-v1.0.6.md` |
| 1.0.6 | Draw Studio v1.0.6 — Tool capabilities and Background Fill | `docs/history/TOOLS-AND-AUTOFILL-v1.0.6.md` |
| 1.0.5 | Speed Optimization — v1.0.5 beta | `docs/history/SPEED-OPTIMIZATION-v1.0.5.md` |
| 1.0.4 | Human Mode — v1.0.4 beta | `docs/history/HUMAN-MODE-v1.0.4.md` |
| 1.0.3 | Draw Quality Upgrade — v1.0.3 beta | `docs/history/DRAW-QUALITY-v1.0.3.md` |
| 1.0.2 | Precision Upgrade — v1.0.2 beta | `docs/history/PRECISION-v1.0.2.md` |
| 0.9.3 | Draw Studio 0.9.3 — Stability Code Audit | `docs/history/CODE-AUDIT-v0.9.3.md` |

## Safety note

Version history is documentation only. Renderer/profile settings cannot disable CanvasGuard, FinalMouseGuard, target monitoring or the no-click safety preflight chain.
