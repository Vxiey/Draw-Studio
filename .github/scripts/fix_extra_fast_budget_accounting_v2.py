from pathlib import Path
import runpy

runpy.run_path('.github/scripts/fix_extra_fast_budget_accounting.py', run_name='__main__')

p=Path('AdaptiveRegionHybrid.py')
text=p.read_text(encoding='utf-8')
old='''def _schedule(choices, sequences_by_component, size, model,options,fill_regions):
    active,usable,fixed_meta,reserve,limit=_budget_seconds(
        options,model,choices,fill_regions,size,size)'''
new='''def _schedule(choices, sequences_by_component, size, model,options,fill_regions,*,fitted=None):
    budget_fitted=tuple(fitted) if fitted is not None else tuple(size)
    active,usable,fixed_meta,reserve,limit=_budget_seconds(
        options,model,choices,fill_regions,size,budget_fitted)'''
if text.count(old)!=1: raise SystemExit(f'schedule fitted anchor count={text.count(old)}')
text=text.replace(old,new)

old='''    groups,sequence,schedule_meta=_schedule(choices,seqs,(pixel_map.width,pixel_map.height),model,options,fill_regions)'''
new='''    groups,sequence,schedule_meta=_schedule(
        choices,seqs,(pixel_map.width,pixel_map.height),model,options,fill_regions,fitted=fitted)'''
if text.count(old)!=1: raise SystemExit(f'build execution schedule call count={text.count(old)}')
text=text.replace(old,new)
p.write_text(text,encoding='utf-8')

p=Path('test_extra_fast_budget_accounting_rc25.py')
text=p.read_text(encoding='utf-8')
old='opts=options(7.0);model=build_cost_model(opts,(500,300),(500,300))'
new='opts=options(5.0);model=build_cost_model(opts,(500,300),(500,300))'
if text.count(old)!=1: raise SystemExit(f'tight budget test anchor count={text.count(old)}')
p.write_text(text.replace(old,new),encoding='utf-8')

print('Extra Fast budget accounting v2 adjustments applied.')
