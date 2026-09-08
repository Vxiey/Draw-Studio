from pathlib import Path
import hashlib
import re
import subprocess
import zipfile

ROOT=Path('.')
PACKAGE='Draw-Studio-1.0.126-beta-Step27.5-One-Click-Setup-Verification.zip'

# Update README without embedding the ZIP hash (which would create a circular build).
readme=Path('README.md')
text=readme.read_text(encoding='utf-8')
new_current='''## Current beta

**v1.0.126-beta — Step 27.5: One-click Setup + Automatic Canvas/Palette Verification**

Current verified source package:

- `Draw-Studio-1.0.126-beta-Step27.5-One-Click-Setup-Verification.zip`
- SHA-256 is published in `SOURCE-PACKAGE-SHA256.txt`

### Step 27.5 highlights

- New **One-click Setup + Verify** action for Microsoft Paint and supported browser drawing games
- Automatically discovers/reuses the target and runs the existing verified canvas/palette setup engine
- Runs a second independent live screenshot verification after initial setup
- Browser verification checks real canvas geometry plus representative saved palette swatches
- Paint verification requires the verified 20-color palette, Pencil + Fill and stable canvas geometry
- Setup never starts drawing and never unlocks mouse/keyboard input
- Failed verification invalidates target/safety readiness and falls back to manual calibration
- Step 27.5 session state is cleared on every profile switch/reset and is not exported in `.drawprofile`
- Step 28–30 keep their existing roadmap numbers
- Windows regression selection: **41/41 passed**

### Step 27 highlights

- Export the selected profile as `.drawprofile` or JSON
- Import target, palette/tool calibration, canvas metadata, renderer settings and CPU/GPU/RAM limits
- Schema-versioned format with migration and strict pre-import validation
- Existing-name conflicts support **Replace**, **Import as copy**, or Cancel
- Import-as-copy gets its own isolated `custom-...` storage key
- Reset only the selected profile to defaults
- Hardware benchmark/timing feedback and all native-input authorization are deliberately excluded
- Imported calibration must pass the normal target/safety verification again before drawing
'''
pattern=r"## Current beta\n.*?(?=\n### Security hotfix)"
text,count=re.subn(pattern,new_current.rstrip(),text,flags=re.S)
if count!=1:raise RuntimeError(f'Could not replace README Current beta block: {count}')
# Quick Start package name.
text=text.replace('Draw-Studio-1.0.125-beta-Step27-Profile-Portability.zip',PACKAGE)
readme.write_text(text,encoding='utf-8')

summary=('v1.0.126-beta Step 27.5: One-click Setup + Automatic Canvas/Palette Verification adds a unified read-only '
         'Paint/browser setup action, independent second-pass live canvas/palette verification, fail-closed confidence '
         'gates and profile-isolated session state without changing Step 28–30 numbering.\n')
for name in ('docs/VERSION-HISTORY.md',):
    p=Path(name);data=p.read_text(encoding='utf-8')
    if not data.startswith(summary):data=summary+data
    row='| 1.0.126-beta Step 27.5 | One-click Setup + Automatic Canvas/Palette Verification | Unified Paint/browser setup, second live canvas/palette verification, fail-closed confidence checks and no drawing authorization. |\n'
    marker='|---|---|---|\n'
    if row not in data and marker in data:data=data.replace(marker,marker+row,1)
    p.write_text(data,encoding='utf-8')

# Root version history also gets the current table row when its table exists.
p=Path('VERSION-HISTORY.md')
if p.exists():
    data=p.read_text(encoding='utf-8')
    row='| 1.0.126-beta Step 27.5 | One-click Setup + Automatic Canvas/Palette Verification | Unified Paint/browser setup, second live canvas/palette verification, fail-closed confidence checks and no drawing authorization. |\n'
    marker='|---|---|---|\n'
    if row not in data and marker in data:data=data.replace(marker,marker+row,1)
    p.write_text(data,encoding='utf-8')

tracked=subprocess.check_output(['git','ls-files'],text=True,encoding='utf-8').splitlines()

def include(path):
    low=path.lower();parts=Path(path).parts
    if low.endswith('.zip') or path=='SOURCE-PACKAGE-SHA256.txt':return False
    if any(part in {'.git','.venv','venv','__pycache__','build','dist'} for part in parts):return False
    if low.endswith(('.pyc','.pyo','.log','.dmp')):return False
    if path in {'step275_integrate_once.py','step275_integrate_once_v2.py','step275_package_once.py'}:return False
    if path=='.github/workflows/step275-integration-once.yml' or path=='.github/workflows/step275-package-once.yml':return False
    if 'safety-report' in low or 'crash-' in low or 'session-' in low:return False
    return Path(path).is_file()

files=sorted(path for path in tracked if include(path))
# Required Step 27.5 release content.
required={'OneClickSetupVerification.py','test_one_click_setup_verification_v10126.py',
          'STEP-27.5-ONE-CLICK-SETUP-VERIFICATION.md','RELEASE-NOTES-v1.0.126-beta-Step27.5.md',
          'Version.py','DrawBot.py','StudioUI.py'}
missing=sorted(required-set(files))
if missing:raise RuntimeError(f'Missing Step 27.5 package files: {missing}')

out=Path(PACKAGE)
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for path in files:z.write(path,path)
with zipfile.ZipFile(out,'r') as z:
    bad=z.testzip();names=set(z.namelist())
    if bad:raise RuntimeError(f'ZIP integrity failed at {bad}')
    if not required.issubset(names):raise RuntimeError('ZIP lost required Step 27.5 files')
    forbidden=[n for n in names if n.startswith('step275_') or 'step275-' in n.lower() or n.lower().endswith('.log') or n.lower().endswith('.pyc')]
    if forbidden:raise RuntimeError(f'Forbidden transient files in ZIP: {forbidden[:10]}')
sha=hashlib.sha256(out.read_bytes()).hexdigest()
Path('SOURCE-PACKAGE-SHA256.txt').write_text(f'{sha}  {PACKAGE}\n',encoding='utf-8')
print(f'PACKAGE={PACKAGE}')
print(f'FILES={len(files)}')
print(f'SIZE={out.stat().st_size}')
print(f'SHA256={sha}')
print('ZIP_INTEGRITY=PASS')
print('STEP275_CONTENT=PASS')
