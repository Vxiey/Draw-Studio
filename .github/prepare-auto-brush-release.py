from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OLD = '1.0.144-rc12'
NEW = '1.0.144-rc13'
SKIP = {
    ROOT / 'RELEASE-NOTES-v1.0.144-rc12.md',
    ROOT / 'VERSION-HISTORY.md',
    ROOT / 'docs/VERSION-HISTORY.md',
    ROOT / '.github/workflows/prepare-auto-brush-release.yml',
    ROOT / '.github/prepare-auto-brush-release.py',
}
BINARY_SUFFIXES = {'.png','.jpg','.jpeg','.gif','.ico','.zip','.exe','.dll','.pyd','.pyc','.bin','.pdf'}

changed = []
for path in ROOT.rglob('*'):
    if not path.is_file() or '.git' in path.parts or path in SKIP or path.suffix.lower() in BINARY_SUFFIXES:
        continue
    try:
        text = path.read_text(encoding='utf-8')
    except (UnicodeDecodeError, OSError):
        continue
    if OLD in text:
        path.write_text(text.replace(OLD, NEW), encoding='utf-8')
        changed.append(path.relative_to(ROOT).as_posix())

help_path = ROOT / 'GettingStarted.py'
help_text = help_path.read_text(encoding='utf-8')
old_help = 'Match the width to the real target tool. A wide brush covers areas faster but can hide small details. A narrow brush preserves edges but needs more strokes. Check the actual mark with a small test.'
new_help = 'This is the Auto Brush baseline. On supported targets, Image Draw Bot verifies available brush sizes and automatically uses broader brushes for large flat regions and smaller brushes for contours, protected details and corrections. Low-confidence layouts keep the fixed baseline and never guess brush-control clicks.'
if old_help not in help_text:
    raise SystemExit('Expected Brush width help text was not found.')
help_path.write_text(help_text.replace(old_help, new_help), encoding='utf-8')

ui_path = ROOT / 'StudioUI.py'
ui_text = ui_path.read_text(encoding='utf-8')
old_ui = "numeric_row(step4, 'Brush width (px)', a.brush_px, 'Match Paint.', width=70)"
new_ui = "numeric_row(step4, 'Brush width (px)', a.brush_px, 'Auto Brush baseline · verified sizes adapt to image detail.', width=70)"
if old_ui not in ui_text:
    raise SystemExit('Expected Brush width UI row was not found.')
ui_path.write_text(ui_text.replace(old_ui, new_ui), encoding='utf-8')

wiki_path = ROOT / 'docs/wiki/Settings-and-Tooltips.md'
if wiki_path.exists():
    wiki = wiki_path.read_text(encoding='utf-8')
    wiki = wiki.replace(old_help, new_help)
    wiki_path.write_text(wiki, encoding='utf-8')

notes = '''# Image Draw Bot v1.0.144-rc13 — Automatic Image-Aware Brush Selection

- Analyze the actual planned image geometry and classify it as detail-heavy, balanced or flat-shape before assigning brush widths.
- Automatically use a broader verified brush for large flat regions when that reduces work without weakening CanvasGuard.
- Automatically downshift to smaller verified brushes for contours, narrow components, protected details, cleanup and accuracy corrections.
- Let supported browser targets reserve a bounded safety inset for one verified automatic brush upshift; very large brush presets are never selected just because they exist.
- Keep low-confidence or incomplete brush-control detection fail-closed: no guessed control clicks and no invented dynamic brush sizes.
- Preserve the existing fixed brush behavior on targets that do not expose verified multi-size controls.
- Add deterministic Auto Brush diagnostics with image classification, selected base/detail/mid sizes, reasons and planned brush-switch counts.
- Update the Brush width help so the value is clearly a baseline for automatic selection rather than a required single fixed width.

This release keeps the existing drawing geometry authoritative. Automatic brush choices are constrained by verified target controls, per-path detail protection and CanvasGuard, and the release remains gated by the complete Windows regression suite, self-test, package validation and silent installer round-trip.
'''
(ROOT / f'RELEASE-NOTES-v{NEW}.md').write_text(notes, encoding='utf-8')

for history_name in ('VERSION-HISTORY.md', 'docs/VERSION-HISTORY.md'):
    history = ROOT / history_name
    if not history.exists():
        continue
    current = history.read_text(encoding='utf-8')
    if f'# Image Draw Bot v{NEW} ' not in current:
        history.write_text(notes.rstrip() + '\n\n' + current.lstrip(), encoding='utf-8')

print(f'Updated {len(changed)} current-version references from {OLD} to {NEW}.')
for name in changed:
    print(name)
