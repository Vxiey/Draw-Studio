from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
source_path = ROOT / 'tools' / 'rebrand_image_draw_bot.py'
code = source_path.read_text(encoding='utf-8')

# GitHub's workflow token may commit normal repository files but cannot update
# workflow definitions. Leave .github/workflows to the authenticated connector.
old = "    if any(part in {'.git', '.build-venv', 'build', 'dist', 'release', '__pycache__'} for part in p.parts):\n        continue"
new = "    if any(part in {'.git', '.build-venv', 'build', 'dist', 'release', '__pycache__'} for part in p.parts) or '.github/workflows/' in p.as_posix():\n        continue"
if old not in code:
    raise SystemExit('Could not patch workflow exclusion in rebrand script')
code = code.replace(old, new, 1)

code = re.sub(
    r"# Release workflow: new public names \+ legacy Setup bridge upload\..*?# README SEO identity \+ current release link\.",
    "# README SEO identity + current release link.",
    code,
    flags=re.S,
)

old_transient = "for transient in (ROOT/'.github/workflows/rebrand-image-draw-bot.yml', ROOT/'tools/rebrand_image_draw_bot.py'):"
new_transient = "for transient in (ROOT/'tools/rebrand_image_draw_bot.py', ROOT/'tools/rebrand_image_draw_bot_v2.py'):"
if old_transient not in code:
    raise SystemExit('Could not patch transient cleanup in rebrand script')
code = code.replace(old_transient, new_transient, 1)

exec(compile(code, str(source_path), 'exec'), {'__file__': str(source_path), '__name__': '__main__'})
