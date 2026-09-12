from pathlib import Path

OLD = '1.0.145-rc23'
NEW = '1.0.145-rc24'


def replace_required(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'Expected release anchor missing in {path}: {old!r}')
    p.write_text(text.replace(old, new), encoding='utf-8')


replace_required('Version.py', f"APP_VERSION = '{OLD}'", f"APP_VERSION = '{NEW}'")
replace_required('installer/ImageDrawBot.iss', f'#define MyAppVersion "{OLD}"', f'#define MyAppVersion "{NEW}"')

# Keep the complete regression suite on the same release version.  Historical
# implementation scripts/release notes are intentionally left untouched.
for test in Path('.').glob('test_*.py'):
    raw = test.read_text(encoding='utf-8')
    if OLD in raw:
        test.write_text(raw.replace(OLD, NEW), encoding='utf-8')

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

notes = '''# Image Draw Bot v1.0.145-rc24 — Regional Axis + Sketch Dense Hybrid

- Add lossless connected-region horizontal/vertical axis planning shared by Extra Fast and Gartic Sketch.
- Let Extra Fast evaluate beneficial tall or run-reducing regions independently instead of rotating an entire same-colour group.
- Keep the existing real execution-cost model and downstream regression guard authoritative; proposals that do not improve the modeled final plan fall back to the baseline.
- Use exact horizontal/vertical run representations for dense Gartic Sketch components when they are cheaper than the junction-heavy contour representation.
- Preserve the contour tracer for thin, structural and diagonal detail.
- Preserve exact source-pixel coverage: no gap bridging, dropped pixels or colour changes.
- Keep protected portrait/detail paths and existing Fill, brush, Paint and profile safety behavior unchanged.
- Synchronize release metadata and the complete regression suite to rc24 so the Windows release gate can validate the actual release version.
'''
Path(f'RELEASE-NOTES-v{NEW}.md').write_text(notes, encoding='utf-8')

history = '''# Image Draw Bot v1.0.145-rc24 — Regional Axis + Sketch Dense Hybrid

- Extra Fast can choose exact horizontal or vertical runs per connected region using the existing execution-cost guard.
- Dense Gartic Sketch regions can use cheaper exact H/V runs while thin structural contours remain on the contour tracer.
- Raster coverage remains exact with no gap bridging or dropped pixels.
- Release metadata, installer and regression version assertions are synchronized atomically.

'''
for name in ('VERSION-HISTORY.md', 'docs/VERSION-HISTORY.md'):
    p = Path(name)
    p.write_text(history + p.read_text(encoding='utf-8'), encoding='utf-8')

# Fail before commit if any active regression still pins the previous release.
stale_tests = [p.as_posix() for p in Path('.').glob('test_*.py') if OLD in p.read_text(encoding='utf-8')]
if stale_tests:
    raise SystemExit('Stale rc23 version assertions remain: ' + ', '.join(stale_tests[:20]))

if NEW not in Path('Version.py').read_text(encoding='utf-8'):
    raise SystemExit('Version.py did not advance to rc24')
if NEW not in Path('installer/ImageDrawBot.iss').read_text(encoding='utf-8'):
    raise SystemExit('Installer metadata did not advance to rc24')
if not Path(f'RELEASE-NOTES-v{NEW}.md').is_file():
    raise SystemExit('rc24 release notes were not created')

print('rc24 release metadata synchronized successfully')
