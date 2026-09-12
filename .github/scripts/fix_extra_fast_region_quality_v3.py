from pathlib import Path
import runpy

runpy.run_path('.github/scripts/fix_extra_fast_region_quality_v2.py', run_name='__main__')

p=Path('AutoDrawing.py')
text=p.read_text(encoding='utf-8')
old="Extra Fast regional hybrid: verified multi-brush regions + structure/detail recovery"
new="Extra Fast regional hybrid: verified multi-brush regions + structure/detail recovery (calibrate Fill to enable buckets)"
if text.count(old)!=1:
    raise SystemExit(f'no-Fill engine label anchor count={text.count(old)}')
p.write_text(text.replace(old,new),encoding='utf-8')
print('Extra Fast Fill guidance compatibility preserved.')
