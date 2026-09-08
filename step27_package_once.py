from pathlib import Path
import hashlib
import subprocess
import zipfile

OLD_PACKAGE='Draw-Studio-1.0.124-beta-Step26-Security-Hotfix.zip'
NEW_PACKAGE='Draw-Studio-1.0.125-beta-Step27-Profile-Portability.zip'
OLD_SHA='989bf626149b851b366f3e03679b69b698ca2d8e5386fab80eb1bfbcfd401436'

# Update public README before packaging. The source ZIP points checksum readers
# back to the repository because a ZIP cannot contain its own final SHA-256.
readme_path=Path('README.md')
readme=readme_path.read_text(encoding='utf-8')
readme=readme.replace(OLD_PACKAGE,NEW_PACKAGE)
readme=readme.replace(f'SHA-256: `{OLD_SHA}`','SHA-256: see `SOURCE-PACKAGE-SHA256.txt` in this repository')
readme=readme.replace(
    '**v1.0.124-beta — Step 26: Detail Fidelity, Pixel-Accurate Planning, Named Color Intelligence & Security Hotfix**',
    '**v1.0.125-beta — Step 27: Export / Import Profiles**'
)
if '- Export/import profiles as portable `.drawprofile` / JSON files' not in readme:
    readme=readme.replace(
        '- Save separate settings for different drawing profiles\n',
        '- Save separate settings for different drawing profiles\n- Export/import profiles as portable `.drawprofile` / JSON files\n',1)
if '- Portable `.drawprofile` / JSON export and import' not in readme:
    readme=readme.replace(
        '- Separate settings per profile\n',
        '- Separate settings per profile\n- Portable `.drawprofile` / JSON export and import\n- Replace / Import as copy conflict handling\n- Reset one profile to Draw Studio defaults without changing other profiles\n',1)
marker='### Security hotfix\n'
step27=(
    '### Step 27 highlights\n\n'
    '- Export the selected profile as `.drawprofile` or JSON\n'
    '- Import target, palette/tool calibration, canvas metadata, renderer settings and CPU/GPU/RAM limits\n'
    '- Schema-versioned format with migration and strict pre-import validation\n'
    '- Existing-name conflicts support **Replace**, **Import as copy**, or Cancel\n'
    '- Import-as-copy gets its own isolated `custom-...` storage key\n'
    '- Reset only the selected profile to defaults\n'
    '- Hardware benchmark/timing feedback and all native-input authorization are deliberately excluded\n'
    '- Imported calibration must pass the normal target/safety verification again before drawing\n\n'
)
if '### Step 27 highlights' not in readme and marker in readme:
    readme=readme.replace(marker,step27+marker,1)
readme_path.write_text(readme,encoding='utf-8')

# Keep the concise history index current.
history_path=Path('docs/VERSION-HISTORY.md')
history=history_path.read_text(encoding='utf-8')
headline='v1.0.125-beta Step 27: Export / Import Profiles adds portable .drawprofile/JSON sharing, schema migration, strict validation, Replace/Import-as-copy conflict handling, per-profile reset and explicit exclusion of machine timing/hardware/input-authorization state.\n'
if not history.startswith('v1.0.125-beta Step 27:'):
    history=headline+history
row='| 1.0.125-beta | Step 27 — Export / Import Profiles | Portable profile sharing with schema migration, pre-import validation, isolated copy/replace handling and reset-to-defaults. |\n'
header='| Version | Name | What changed |\n|---|---|---|\n'
if row not in history and header in history:
    history=history.replace(header,header+row,1)
history_path.write_text(history,encoding='utf-8')

# Build a clean source package from tracked project files only.
tracked=subprocess.check_output(['git','ls-files'],text=True,encoding='utf-8').splitlines()
skip_dirs={'.git','.github','.venv','__pycache__','build','dist','release','logs','safety-reports'}
skip_files={'SOURCE-PACKAGE-SHA256.txt','step27_package_once.py'}
files=[]
for raw in tracked:
    path=Path(raw)
    if not path.is_file():
        continue
    if any(part in skip_dirs for part in path.parts):
        continue
    if path.name in skip_files:
        continue
    if path.name.startswith('Draw-Studio-') and path.suffix.lower()=='.zip':
        continue
    if path.suffix.lower() in {'.pyc','.log','.dmp'}:
        continue
    files.append(path)

out=Path(NEW_PACKAGE)
if out.exists(): out.unlink()
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
    for path in sorted(files,key=lambda p:p.as_posix().lower()):
        zf.write(path,('Draw-Studio/'+path.as_posix()))

with zipfile.ZipFile(out,'r') as zf:
    bad=zf.testzip()
    if bad:
        raise SystemExit(f'ZIP integrity failed at {bad}')
    names=set(zf.namelist())
    required={
        'Draw-Studio/Version.py','Draw-Studio/ProfilePortability.py',
        'Draw-Studio/test_profile_portability_step27.py','Draw-Studio/StudioUI.py',
        'Draw-Studio/RELEASE-NOTES-v1.0.125-beta-Step27.md',
        'Draw-Studio/STEP-27-PROFILE-PORTABILITY.md',
    }
    missing=sorted(required-names)
    if missing: raise SystemExit('Missing Step 27 release files: '+', '.join(missing))
    version=zf.read('Draw-Studio/Version.py').decode('utf-8')
    if "APP_VERSION = '1.0.125-beta'" not in version:
        raise SystemExit('Packaged version is not 1.0.125-beta')
    portability=zf.read('Draw-Studio/ProfilePortability.py').decode('utf-8')
    for needle in ('SCHEMA_VERSION = 1','import_package_into_app','reset_profile_dialog','machine_specific_state_included'):
        if needle not in portability: raise SystemExit(f'Missing Step 27 feature marker: {needle}')

digest=hashlib.sha256(out.read_bytes()).hexdigest()
Path('SOURCE-PACKAGE-SHA256.txt').write_text(f'{digest}  {NEW_PACKAGE}\n',encoding='utf-8')

# Repository README can now show the final hash; ZIP README intentionally points
# to the repository checksum file to avoid self-referential hashing.
readme=readme_path.read_text(encoding='utf-8')
readme=readme.replace('SHA-256: see `SOURCE-PACKAGE-SHA256.txt` in this repository',f'SHA-256: `{digest}`')
readme_path.write_text(readme,encoding='utf-8')

print('PACKAGE='+NEW_PACKAGE)
print('FILES='+str(len(files)))
print('SIZE='+str(out.stat().st_size))
print('SHA256='+digest)
print('ZIP_INTEGRITY=PASS')
print('STEP27_CONTENT=PASS')
