from pathlib import Path

path=Path(__file__).resolve().parent/'PreviewDiagnostics.py'
text=path.read_text(encoding='utf-8')
old="    hybrid=diagnostics.get('hybrid_renderer') or {}\n"
new="    hybrid=meta.get('hybrid_renderer') or {}\n"
if old in text:
    text=text.replace(old,new,1)
elif new not in text:
    raise RuntimeError('Hybrid preview diagnostics formatter anchor not found')
path.write_text(text,encoding='utf-8',newline='\n')
print('PreviewDiagnostics Step 29 NameError fixed for RC.')
