from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_APP = '1.0.144-rc14'
NEW_APP = '1.0.145-rc1'
OLD_FILE = '1.0.144'
NEW_FILE = '1.0.145'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, text):
    (ROOT / path).write_text(text, encoding='utf-8')


def replace_required(path, old, new):
    text = read(path)
    if old not in text:
        raise RuntimeError(f'{path}: missing expected text {old!r}')
    write(path, text.replace(old, new))


# Canonical runtime/package metadata.
replace_required('Version.py', "APP_VERSION = '1.0.144-rc14'", "APP_VERSION = '1.0.145-rc1'")
replace_required('Version.py', "FILE_VERSION = '1.0.144'", "FILE_VERSION = '1.0.145'")
replace_required('installer/ImageDrawBot.iss', '#define MyAppVersion "1.0.144-rc14"', '#define MyAppVersion "1.0.145-rc1"')

# Current-release documentation. Historical rc14 notes/history remain intact.
for path in [
    'README.md',
    'README-INDEX.md',
    'docs/README.md',
    'docs/wiki/Home.md',
    'docs/wiki/Installation.md',
    'docs/wiki/Updates.md',
]:
    replace_required(path, OLD_APP, NEW_APP)

# Active-version regression assertions. Do not rewrite historical prose.
changed_tests = 0
for p in ROOT.glob('test_*.py'):
    text = p.read_text(encoding='utf-8')
    if OLD_APP not in text:
        continue
    new = text.replace(OLD_APP, NEW_APP)
    # Version assertion files pair APP_VERSION with FILE_VERSION. Update only
    # these test files, not historical release documentation.
    new = new.replace("FILE_VERSION,'1.0.144'", "FILE_VERSION,'1.0.145'")
    new = new.replace('FILE_VERSION,"1.0.144"', 'FILE_VERSION,"1.0.145"')
    new = new.replace("FILE_VERSION, '1.0.144'", "FILE_VERSION, '1.0.145'")
    new = new.replace('FILE_VERSION, "1.0.144"', 'FILE_VERSION, "1.0.145"')
    p.write_text(new, encoding='utf-8')
    changed_tests += 1
if not changed_tests:
    raise RuntimeError('No active-version tests were updated.')

notes = '''# Image Draw Bot v1.0.145-rc1 — Verified Drawing Baseline

- Start the 1.0.145 release-candidate line from the fully verified 1.0.144-rc14 drawing stack.
- Keep the live drawing timer and measured **Total draw time** shown after completed drawings.
- Keep **Brush width: Auto** as the default, including image/canvas-aware pixel-width selection and manual 1–50 px override.
- Keep Microsoft Paint pixel-size preparation through verified UI Automation rather than forcing a fixed 1 px size.
- Preserve profile-isolated ETA learning, CanvasGuard, cancellation, calibration, preview safety and existing rendering-mode behavior.
- No deliberate drawing-quality or compatibility regression is introduced by this version transition.
'''
write('RELEASE-NOTES-v1.0.145-rc1.md', notes)

history = '''# Image Draw Bot v1.0.145-rc1 — Verified Drawing Baseline

- Begin the 1.0.145 release-candidate line from the verified rc14 runtime.
- Retain Total Draw Timer, Automatic Pixel Brush, Paint UI Automation sizing and profile-isolated ETA calibration.
- Preserve existing drawing-engine, calibration, preview, profile and cancellation behavior.

'''
for path in ['VERSION-HISTORY.md', 'docs/VERSION-HISTORY.md']:
    current = read(path)
    if current.startswith('# Image Draw Bot v1.0.145-rc1'):
        raise RuntimeError(f'{path}: rc1 block already exists')
    write(path, history + current)

# Consistency gates before anything is committed.
version = read('Version.py')
if "APP_VERSION = '1.0.145-rc1'" not in version or "FILE_VERSION = '1.0.145'" not in version:
    raise RuntimeError('Version.py did not reach 1.0.145-rc1 / 1.0.145')
for p in ROOT.glob('test_*.py'):
    text = p.read_text(encoding='utf-8')
    if OLD_APP in text:
        raise RuntimeError(f'{p.name}: stale active APP_VERSION assertion remains')
print(f'Prepared Image Draw Bot {NEW_APP}; updated {changed_tests} active-version test files.')
