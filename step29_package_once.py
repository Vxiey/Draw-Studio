from __future__ import annotations

from pathlib import Path
import hashlib
import os
import re
import zipfile

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / 'Draw-Studio-1.0.128-beta-Step29-Hybrid-Renderer-3.zip'
PACKAGE_NAME = PACKAGE.name


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding='utf-8')
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f'{path.name}: expected README/history block was not found')
    path.write_text(text.replace(old, new, 1), encoding='utf-8', newline='\n')


def prepare_docs() -> None:
    readme = ROOT / 'README.md'
    text = readme.read_text(encoding='utf-8')

    # Quick Start was still pointing at the older Step 27.5 package.
    text = text.replace(
        '`Draw-Studio-1.0.126-beta-Step27.5-One-Click-Setup-Verification.zip`',
        f'`{PACKAGE_NAME}`'
    )

    old_current = '''## Current beta

**v1.0.127-beta — Step 28: More Drawing Targets**

Current verified source package:

- `Draw-Studio-1.0.127-beta-Step28-More-Drawing-Targets.zip`
- SHA-256 is published in `SOURCE-PACKAGE-SHA256.txt`

### Step 28 highlights
'''
    new_current = f'''## Current beta

**v1.0.128-beta — Step 29: Hybrid Renderer 3.0**

Current verified source package:

- `{PACKAGE_NAME}`
- SHA-256 is published in `SOURCE-PACKAGE-SHA256.txt`

### Step 29 highlights

- New **Hybrid Renderer 3.0** rendering style
- **Auto Hybrid** uses bounded local Pillow/NumPy structure analysis — no AI, ML or OCR
- Dedicated **Pixel Art** mode routes into full-resolution Pixel Accurate planning
- **Icon / Logo** uses safe Fill + contour + structural detail passes
- **Line Art** uses contour-first Better Shapes v2 with structural-line preservation
- **Portrait** reuses PortraitPlanner for single-colour targets and high-detail perceptual planning for colour targets
- **Shaded Object** uses progressive base, shade/highlight, contour and detail passes
- **Deadline Silhouette** prioritizes a recognizable subject under short time budgets
- Hybrid policy cannot modify CanvasGuard, target locks, calibration, preflight, dry-run or Start authorization
- Hybrid mode is saved per profile and supported by `.drawprofile` export/import
- Preview diagnostics show requested/resolved Hybrid mode, passes and source-analysis metrics
- Windows Step 29 regression selection: **64/64 passed**
- Step 30 remains **Release Candidate Hardening**

### Step 28 highlights
'''
    if old_current not in text and new_current not in text:
        raise RuntimeError('README Current beta Step 28 block not found')
    if old_current in text:
        text = text.replace(old_current, new_current, 1)
    readme.write_text(text, encoding='utf-8', newline='\n')

    history_line = (
        'v1.0.128-beta Step 29: Hybrid Renderer 3.0 adds deterministic Auto Hybrid plus Pixel Art, '
        'Icon / Logo, Line Art, Portrait, Shaded Object and Deadline Silhouette modes; it reuses the '
        'existing Pixel Accurate, Quick Sketch, Shape Paths and PortraitPlanner engines while preserving '
        'CanvasGuard, calibration and profile isolation.\n'
    )
    for name in ('VERSION-HISTORY.md', 'docs/VERSION-HISTORY.md'):
        path = ROOT / name
        old = path.read_text(encoding='utf-8')
        if not old.startswith(history_line):
            path.write_text(history_line + old, encoding='utf-8', newline='\n')


def excluded(rel: Path) -> bool:
    parts = set(rel.parts)
    if parts & {'.git', '.venv', '.build-venv', '__pycache__', '.pytest_cache', '.mypy_cache',
                'build', 'dist', 'safety-reports', 'crash-dumps'}:
        return True
    name = rel.name.lower()
    if name.endswith(('.pyc', '.pyo', '.log', '.dmp', '.tmp')):
        return True
    if name.startswith('draw-studio-') and name.endswith('.zip'):
        return True
    if re.fullmatch(r'step\d+(?:\d+)?_.*_once\.py', rel.name, flags=re.I):
        return True
    if rel.as_posix().startswith('.github/workflows/') and 'step29' in name and 'once' in name:
        return True
    return False


def build_zip() -> tuple[int, int, str]:
    if PACKAGE.exists():
        PACKAGE.unlink()
    files = []
    for path in ROOT.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if excluded(rel):
            continue
        files.append((rel.as_posix(), path))
    files.sort(key=lambda item: item[0].lower())

    with zipfile.ZipFile(PACKAGE, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel, path in files:
            zf.write(path, f'Draw-Studio/{rel}')

    with zipfile.ZipFile(PACKAGE, 'r') as zf:
        bad = zf.testzip()
        if bad is not None:
            raise RuntimeError(f'ZIP integrity failed at {bad}')
        names = set(zf.namelist())
        required = {
            'Draw-Studio/HybridRenderer3.py',
            'Draw-Studio/STEP-29-HYBRID-RENDERER-3.md',
            'Draw-Studio/RELEASE-NOTES-v1.0.128-beta-Step29.md',
            'Draw-Studio/DrawBot.py',
            'Draw-Studio/StudioUI.py',
            'Draw-Studio/Version.py',
        }
        missing = sorted(required - names)
        if missing:
            raise RuntimeError('Step 29 package is missing: ' + ', '.join(missing))
        forbidden = [n for n in names if (
            n.endswith('step29_integrate_once.py') or
            n.endswith('step29_package_once.py') or
            ('/.github/workflows/' in n and 'step29' in n.lower() and 'once' in n.lower()) or
            '/__pycache__/' in n or n.lower().endswith(('.pyc','.log','.dmp'))
        )]
        if forbidden:
            raise RuntimeError('Temporary/runtime files leaked into ZIP: ' + ', '.join(forbidden[:8]))
        version = zf.read('Draw-Studio/Version.py').decode('utf-8')
        if "APP_VERSION = '1.0.128-beta'" not in version or 'FILE_VERSION = "1.0.128"' not in version:
            raise RuntimeError('Packaged Version.py does not identify v1.0.128-beta')
        hybrid = zf.read('Draw-Studio/HybridRenderer3.py').decode('utf-8')
        for token in ('Auto Hybrid','Pixel Art','Icon / Logo','Line Art','Portrait','Shaded Object','Deadline Silhouette'):
            if token not in hybrid:
                raise RuntimeError(f'Hybrid mode missing from package: {token}')

    digest = hashlib.sha256(PACKAGE.read_bytes()).hexdigest()
    size = PACKAGE.stat().st_size
    return len(files), size, digest


def main() -> None:
    prepare_docs()
    files, size, digest = build_zip()
    (ROOT / 'SOURCE-PACKAGE-SHA256.txt').write_text(
        f'{digest}  {PACKAGE_NAME}\n', encoding='utf-8', newline='\n')
    print(f'PACKAGE={PACKAGE_NAME}')
    print(f'FILES={files}')
    print(f'SIZE={size}')
    print(f'SHA256={digest}')
    print('ZIP_INTEGRITY=PASS')
    print('STEP29_CONTENT=PASS')
    print('TEMP_FILES_EXCLUDED=PASS')


if __name__ == '__main__':
    main()
