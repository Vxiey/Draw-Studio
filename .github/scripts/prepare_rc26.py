from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = '1.0.145-rc25'
NEW = '1.0.145-rc26'
TITLE = '# Image Draw Bot v1.0.145-rc26 — Gartic Google Drop-In & Canvas Detection\n'


def replace_required(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'{path.relative_to(ROOT)} does not contain expected {old!r}')
    path.write_text(text.replace(old, new), encoding='utf-8')


def replace_if_present(path: Path, old: str, new: str) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding='utf-8')
    if old in text:
        path.write_text(text.replace(old, new), encoding='utf-8')


replace_required(ROOT / 'Version.py', OLD, NEW)
replace_required(ROOT / 'installer' / 'ImageDrawBot.iss', OLD, NEW)

changed_tests = 0
for path in ROOT.rglob('test_*.py'):
    if '.git' in path.parts:
        continue
    text = path.read_text(encoding='utf-8')
    if OLD in text:
        path.write_text(text.replace(OLD, NEW), encoding='utf-8')
        changed_tests += 1

for relative in (
    'README.md',
    'README-INDEX.md',
    'docs/README.md',
    'docs/wiki/Home.md',
    'docs/wiki/Installation.md',
    'docs/wiki/Updates.md',
):
    replace_if_present(ROOT / relative, OLD, NEW)

notes = ROOT / f'RELEASE-NOTES-v{NEW}.md'
notes.write_text(
    TITLE
    + '\n'
    + '- Drag images from Google Images, Chrome or Edge directly onto the detected Gartic Phone canvas through Drop-In Start.\n'
    + '- Accept bounded browser `data:image/...;base64` drag payloads in addition to local files, HTTP(S) image URLs and existing Google/Bing redirect handling.\n'
    + '- Improve Gartic Phone canvas detection by ranking multiple plausible regions instead of assuming the largest white component is the canvas.\n'
    + '- Add a conservative Gartic violet-frame/aspect fallback so a partly drawn canvas can still be rediscovered without guessing arbitrary coordinates.\n'
    + '- Keep Browser Auto Calibration edge refinement and CanvasGuard verification authoritative before native drawing input.\n'
    + '- Arm Drop-In Start can discover the Gartic canvas read-only even before palette/setup is complete; the accepted image then goes through Browser One-Click verification before drawing.\n'
    + '- Add global F1 Quick Start. It uses the normal setup guard, temporary unlock and Start flow; Paint continues through Prepare Paint & draw.\n'
    + '- Preserve rc25 Extra Fast regional scheduling, five-brush Gartic execution, Fill safety and preview/execution parity.\n'
    + '- Synchronize installer metadata, current documentation and active regression version assertions to rc26.\n',
    encoding='utf-8',
)

history_entry = (
    TITLE
    + '\n'
    + '- Google/Chromium image drags can be released directly over the detected Gartic canvas and continue through the guarded Browser One-Click start path.\n'
    + '- Gartic canvas discovery now ranks multiple candidates and has a conservative violet-frame fallback for partly drawn canvases.\n'
    + '- F1 Quick Start uses the existing safety/setup path instead of bypassing it.\n'
    + '- rc25 Extra Fast regional planning and the five-brush Gartic ladder remain intact.\n\n'
)
for relative in ('VERSION-HISTORY.md', 'docs/VERSION-HISTORY.md'):
    path = ROOT / relative
    current = path.read_text(encoding='utf-8')
    if TITLE.strip() not in current:
        path.write_text(history_entry + current, encoding='utf-8')

remaining = []
for path in ROOT.rglob('test_*.py'):
    if '.git' in path.parts:
        continue
    if OLD in path.read_text(encoding='utf-8'):
        remaining.append(path.relative_to(ROOT).as_posix())
if remaining:
    raise SystemExit('Active version tests still pinned to rc25: ' + ', '.join(remaining[:20]))

version_text = (ROOT / 'Version.py').read_text(encoding='utf-8')
installer_text = (ROOT / 'installer' / 'ImageDrawBot.iss').read_text(encoding='utf-8')
if f"APP_VERSION = '{NEW}'" not in version_text:
    raise SystemExit('Version.py was not synchronized to rc26')
if f'#define MyAppVersion "{NEW}"' not in installer_text:
    raise SystemExit('Installer was not synchronized to rc26')
if not notes.is_file() or not notes.read_text(encoding='utf-8').strip():
    raise SystemExit('rc26 release notes were not created')
print(f'Prepared {NEW}; synchronized {changed_tests} active test files.')
