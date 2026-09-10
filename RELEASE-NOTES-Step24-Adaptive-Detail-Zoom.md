# Image Draw Bot v1.0.124-beta — Step 24 Adaptive Detail Zoom

- Adds Auto / Off / 2x / 4x internal source-detail zoom.
- Recovers thin lines, small color accents and high-frequency micro details lost by global downsampling.
- Uses existing OKLab/Faithful color matching rather than a separate color engine.
- Keeps the target application at its existing zoom; canvas calibration never moves.
- Adds a Detail zoom preview tab and diagnostics metadata.
- Uses bounded path budgets: very small under 75/80 second game deadlines, larger for 150/300/unlimited work.
- Recovered detail paths are optional under deadline scheduling and may be dropped by Panic Mode.
- Pixel Accurate bypasses the pass because full target pixels are already preserved.
