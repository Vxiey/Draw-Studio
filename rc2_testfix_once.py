from pathlib import Path

path = Path(__file__).resolve().parent / 'test_step30_release_candidate_hardening_v10129rc1.py'
text = path.read_text(encoding='utf-8')
text = text.replace('(1,0,129,0)', '(1,0,130,0)')
path.write_text(text, encoding='utf-8')
print('RC2 version_info test fixture corrected')
