from pathlib import Path

path=Path(__file__).resolve().parent/'README.md'
text=path.read_text(encoding='utf-8')
package='Draw-Studio-1.0.129-rc1-Step30-Release-Candidate-Hardening.zip'
marker='**v1.0.129-rc1 — Step 30: Release Candidate Hardening**'
if marker not in text:
    start=text.find('## Current beta')
    if start < 0:
        start=text.find('## Current release candidate')
    end=text.find('### Step 29 highlights',start if start >= 0 else 0)
    if start < 0 or end < 0:
        raise RuntimeError('README current-release section anchors not found')
    replacement=f'''## Current release candidate

{marker}

Current RC source package:

- `{package}`
- SHA-256 is published in `SOURCE-PACKAGE-SHA256.txt` after packaging

### Step 30 highlights

- Numbered feature roadmap is frozen for RC validation
- 5,000-cycle start/stop/disarm lifecycle soak gate
- Repeated profile-storage isolation soak
- Update Center fixed to `Vxiey/Draw-Studio` with RC-aware channel filtering
- Version.py, PE metadata and Inno Setup version consistency gates
- Windows ZIP/installer/SHA-256/manifest validation
- Silent installer → installed EXE self-test → silent uninstall in Windows CI
- Source/release packages reject logs, dumps, bytecode, tests and one-time patch files
- Full regression discovery is a release gate
- Hybrid Renderer 3.0 remains the current renderer; no new renderer feature is added by Step 30

'''
    text=text[:start]+replacement+text[end:]
text=text.replace('`Draw-Studio-1.0.128-beta-Step29-Hybrid-Renderer-3.zip`',f'`{package}`')
path.write_text(text,encoding='utf-8',newline='\n')
print('README RC section prepared.')
