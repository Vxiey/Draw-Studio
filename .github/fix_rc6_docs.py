from pathlib import Path

version = "1.0.145-rc6"
previous = "1.0.145-rc5"

readme = Path("README.md")
text = readme.read_text(encoding="utf-8")
if previous not in text:
    raise SystemExit("README current rc5 references were not found")
text = text.replace(previous, version)
readme.write_text(text, encoding="utf-8")

history = Path("VERSION-HISTORY.md")
text = history.read_text(encoding="utf-8")
heading = f"# Image Draw Bot v{version} — Region Brush Packing"
if heading not in text:
    entry = f'''{heading}\n\n- Added exact multi-brush region packing for verified browser brush ladders such as Gartic 2 / 4 / 8 / 16 / 28 px.\n- Large safe interiors are packed largest-first, then smaller verified brushes repair remaining pixels.\n- Every emitted brush footprint is simulated against the exact connected component; unsafe or incomplete candidates fall back to connected runs.\n- Fixed even-sized brush erosion so planner safety matches the real 2/4/8/16/28 px execution footprint.\n- Removed the old 1 px brush requirement and stopped isolated hybrid paths from requesting a brush control that the target does not expose.\n\n'''
    text = entry + text
    history.write_text(text, encoding="utf-8")

print("rc6 README and version history updated")
