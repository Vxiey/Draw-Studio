from pathlib import Path
import hashlib
import re
import zipfile

ROOT=Path(__file__).resolve().parent
NAME='Draw-Studio-1.0.127-beta-Step28-More-Drawing-Targets.zip'
OUT=ROOT/NAME

EXCLUDE_DIRS={'.git','.venv','__pycache__','.pytest_cache','.mypy_cache','build','dist','logs','safety-reports','diagnostics'}
EXCLUDE_FILES={
    'step28_integrate_once.py','step28_package_once.py',
    '.github/workflows/step28-integration-once.yml',
    '.github/workflows/step28-package-once.yml',
}


def include(path: Path) -> bool:
    rel=path.relative_to(ROOT).as_posix()
    if any(part in EXCLUDE_DIRS for part in path.relative_to(ROOT).parts):return False
    if rel in EXCLUDE_FILES:return False
    if rel.startswith('.github/workflows/') and ('once' in rel.lower() or 'step28' in rel.lower()):return False
    if path.suffix.lower() in {'.pyc','.pyo','.log','.dmp'}:return False
    if path.name.endswith('.marker'):return False
    if path.suffix.lower()=='.zip':return False
    if path.name=='SOURCE-PACKAGE-SHA256.txt':return False
    return path.is_file()


def update_readme():
    p=ROOT/'README.md'; text=p.read_text(encoding='utf-8')
    marker='### Step 27.5 highlights'
    if marker not in text:raise RuntimeError('README Step 27.5 marker missing')
    start=text.index('## Current beta')
    mid=text.index(marker,start)
    new='''## Current beta

**v1.0.127-beta — Step 28: More Drawing Targets**

Current verified source package:

- `Draw-Studio-1.0.127-beta-Step28-More-Drawing-Targets.zip`
- SHA-256 is published in `SOURCE-PACKAGE-SHA256.txt`

### Step 28 highlights

- New dedicated **Kleki** browser-painting profile
- New dedicated **Magma** collaborative-browser profile
- Central `TargetCapabilities` registry for desktop/browser/manual/automatic target semantics
- Verified Browser Auto Setup remains limited to Gartic Phone, Skribbl.io/Fast, SketchHeads and Sketchful.io
- Drawize, Gartic.io, Kleki and Magma intentionally use explicit manual tool/palette/canvas calibration until a current detector is verified
- Automatic browser controls are hidden for manual targets instead of pretending unsupported layouts are safe
- Every target retains isolated settings, palette, tools, layout fingerprint, verified-color cache and timing storage
- No target profile contains native handles, input authorization or hard-coded screen coordinates
- Step 29 and Step 30 keep their roadmap numbers
- Windows Step 28 regression selection: **59/59 passed**

'''
    text=text[:start]+new+text[mid:]
    p.write_text(text,encoding='utf-8')


def prepend_history(path: Path):
    if not path.exists():return
    text=path.read_text(encoding='utf-8')
    line='v1.0.127-beta Step 28: More Drawing Targets adds the TargetCapabilities registry plus isolated Kleki and Magma profiles; unverified browser targets remain manual by design and cannot inherit verified auto-setup semantics.\n'
    if 'v1.0.127-beta Step 28:' not in text:
        path.write_text(line+text,encoding='utf-8')


update_readme()
prepend_history(ROOT/'VERSION-HISTORY.md')
prepend_history(ROOT/'docs'/'VERSION-HISTORY.md')

if OUT.exists():OUT.unlink()
files=sorted((p for p in ROOT.rglob('*') if include(p)),key=lambda p:p.relative_to(ROOT).as_posix().lower())
with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for path in files:
        z.write(path,path.relative_to(ROOT).as_posix())

with zipfile.ZipFile(OUT,'r') as z:
    bad=z.testzip()
    if bad:raise RuntimeError(f'ZIP integrity failure: {bad}')
    names=set(z.namelist())
    required={
        'Version.py','TargetCapabilities.py','GameProfiles.py','ProfileEngine.py',
        'OneClickSetupVerification.py','RELEASE-NOTES-v1.0.127-beta-Step28.md',
        'STEP-28-MORE-DRAWING-TARGETS.md','test_target_capabilities_v10127.py',
        'test_step28_more_targets_v10127.py'
    }
    missing=required-names
    if missing:raise RuntimeError(f'Missing Step 28 package files: {sorted(missing)}')
    forbidden=[n for n in names if n in EXCLUDE_FILES or n.endswith('.pyc') or '__pycache__/' in n or n.endswith('.log')]
    if forbidden:raise RuntimeError(f'Forbidden release files: {forbidden[:12]}')
    version=z.read('Version.py').decode('utf-8')
    if "APP_VERSION = '1.0.127-beta'" not in version:raise RuntimeError('Wrong version inside ZIP')
    profiles=z.read('GameProfiles.py').decode('utf-8')
    if "'Kleki':('kleki'" not in profiles or "'Magma':('magma'" not in profiles:raise RuntimeError('New Step 28 profiles missing')

sha=hashlib.sha256(OUT.read_bytes()).hexdigest()
(ROOT/'SOURCE-PACKAGE-SHA256.txt').write_text(f'{sha}  {NAME}\n',encoding='utf-8')
print(f'PACKAGE={NAME}')
print(f'FILES={len(files)}')
print(f'SIZE={OUT.stat().st_size}')
print(f'SHA256={sha}')
print('ZIP_INTEGRITY=PASS')
print('STEP28_CONTENT=PASS')
