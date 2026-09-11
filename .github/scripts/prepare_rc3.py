from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = '1.0.145-rc2'
NEW = '1.0.145-rc3'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, text):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


def replace_required(path, old, new):
    text = read(path)
    if old not in text:
        raise RuntimeError(f'Expected release anchor not found in {path}: {old!r}')
    write(path, text.replace(old, new))


replace_required('Version.py', "APP_VERSION = '1.0.145-rc2'", "APP_VERSION = '1.0.145-rc3'")
replace_required('installer/ImageDrawBot.iss', '#define MyAppVersion "1.0.145-rc2"', '#define MyAppVersion "1.0.145-rc3"')

for rel in (
    'README.md',
    'docs/wiki/Installation.md',
    'docs/README.md',
    'README-INDEX.md',
    'docs/wiki/Home.md',
    'docs/wiki/Updates.md',
):
    p = ROOT / rel
    if p.exists():
        text = p.read_text(encoding='utf-8')
        if OLD in text:
            p.write_text(text.replace(OLD, NEW), encoding='utf-8')

for p in ROOT.glob('test_*.py'):
    text = p.read_text(encoding='utf-8')
    if OLD in text:
        p.write_text(text.replace(OLD, NEW), encoding='utf-8')

notes = '''# Image Draw Bot v1.0.145-rc3 — Fill, Brush and ETA Reliability

- Bound stateful Fill safety simulation to local ROIs while preserving global coverage state, reducing repeated full-canvas allocations.
- Make Extra Fast and RegionFill economics batch-aware so same-color Fill candidates are not penalized by duplicated tool-switch overhead.
- Improve adaptive brush planning with geometry-aware brush selection and collapse transient speed-only upshifts that would cost more UI switching than they save.
- Estimate draw time from the final execution sequence, including actual color, brush, Fill, verification and tool transitions instead of relying only on planner summary estimates.
- Keep existing browser CanvasGuard limits authoritative; full Gartic 5-brush CanvasGuard support remains follow-up work rather than being claimed complete in this RC.
- Include regression coverage for the Fill ROI allocation and batch/sequence cost-model fixes.
'''
write(f'RELEASE-NOTES-v{NEW}.md', notes)

for rel in ('VERSION-HISTORY.md', 'docs/VERSION-HISTORY.md'):
    p = ROOT / rel
    old = p.read_text(encoding='utf-8') if p.exists() else ''
    if not old.startswith(f'# Image Draw Bot v{NEW}'):
        p.write_text(notes + '\n' + old, encoding='utf-8')

write('.github/release-build-trigger', f'{NEW} fill-brush-eta-reliability publish\n')

(ROOT / '.github/scripts/prepare_rc3.py').unlink(missing_ok=True)
(ROOT / '.github/workflows/prepare-rc3.yml').unlink(missing_ok=True)
