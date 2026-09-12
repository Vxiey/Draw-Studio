from pathlib import Path

OLD = '1.0.145-rc24'
NEW = '1.0.145-rc25'


def replace_required(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'Expected release anchor missing in {path}: {old!r}')
    p.write_text(text.replace(old, new), encoding='utf-8')


replace_required('Version.py', f"APP_VERSION = '{OLD}'", f"APP_VERSION = '{NEW}'")
replace_required('installer/ImageDrawBot.iss', f'#define MyAppVersion "{OLD}"', f'#define MyAppVersion "{NEW}"')

# Synchronize only active regression files. Historical implementation scripts,
# old release notes and prior version-history entries must remain immutable.
for test in Path('.').glob('test_*.py'):
    raw = test.read_text(encoding='utf-8')
    if OLD in raw:
        test.write_text(raw.replace(OLD, NEW), encoding='utf-8')

# Current-facing documentation and release links should point at rc25.
for name in (
    'README.md',
    'README-INDEX.md',
    'docs/README.md',
    'docs/wiki/Home.md',
    'docs/wiki/Installation.md',
    'docs/wiki/Updates.md',
):
    p = Path(name)
    if p.exists():
        raw = p.read_text(encoding='utf-8')
        if OLD in raw:
            p.write_text(raw.replace(OLD, NEW), encoding='utf-8')

notes = '''# Image Draw Bot v1.0.145-rc25 — Extra Fast Regional Quality Fix

- Replace destructive Extra Fast path-count truncation with Adaptive Region Hybrid scheduling for normal full-colour runs.
- Schedule whole connected regions by visual value against the real execution-cost/time model instead of dropping large portions of a portrait after planning.
- Preserve Gartic's verified five-brush ladder (2/4/8/16/28 px) through per-path brush execution so large safe regions are not forced through the smallest brush.
- Force Extra Fast detail policy back to Auto so stale saved Strong simplify settings cannot erase important facial, contour or small-object structure before planning.
- Treat the adaptive regional plan as a first-class prebuilt execution plan so generic path caps, stroke optimizers and a second deadline pass cannot prune it again.
- Make Simulated final rasterize the same regional execution sequence and per-path brush widths used by Draw.
- Preserve the proven legacy Fill route when a profile advertises Fill capability but has no executable Fill actions; calibrated Fill and no-Fill browser runs use the regional route safely.
- Keep rc24's exact connected-region H/V planning and Sketch dense fallback, while improving real Extra Fast quality/execution parity.
- Synchronize installer, current-facing documentation and regression version assertions atomically to rc25.
'''
Path(f'RELEASE-NOTES-v{NEW}.md').write_text(notes, encoding='utf-8')

history = '''# Image Draw Bot v1.0.145-rc25 — Extra Fast Regional Quality Fix

- Extra Fast now budgets whole connected regions instead of destructively truncating individual paths after planning.
- Gartic keeps the verified 2/4/8/16/28 px brush ladder and the regional scheduler can spend time on large safe coverage before structure/detail recovery.
- Simulated final now follows the same adaptive regional execution sequence as the real draw, including per-path brush widths.
- Stale Strong simplify settings no longer leak into Extra Fast.
- Existing calibrated Fill safety and the rc24 exact H/V raster guarantees remain intact.
- Release metadata, installer and active regression version assertions are synchronized atomically.

'''
for name in ('VERSION-HISTORY.md', 'docs/VERSION-HISTORY.md'):
    p = Path(name)
    p.write_text(history + p.read_text(encoding='utf-8'), encoding='utf-8')

# Fail before commit if any active regression still pins rc24.
stale_tests = [p.as_posix() for p in Path('.').glob('test_*.py') if OLD in p.read_text(encoding='utf-8')]
if stale_tests:
    raise SystemExit('Stale rc24 version assertions remain: ' + ', '.join(stale_tests[:20]))

checks = {
    'Version.py': NEW,
    'installer/ImageDrawBot.iss': NEW,
    'README.md': NEW,
    'VERSION-HISTORY.md': NEW,
    'docs/VERSION-HISTORY.md': NEW,
}
for path, needle in checks.items():
    if needle not in Path(path).read_text(encoding='utf-8'):
        raise SystemExit(f'rc25 synchronization failed for {path}')
if not Path(f'RELEASE-NOTES-v{NEW}.md').is_file():
    raise SystemExit('rc25 release notes were not created')

# Historical rc24 notes must remain present and unchanged as a release record.
if not Path(f'RELEASE-NOTES-v{OLD}.md').is_file():
    raise SystemExit('Historical rc24 release notes unexpectedly missing')

print('rc25 release metadata synchronized successfully')
