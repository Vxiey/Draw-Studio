from pathlib import Path

p=Path('.github/scripts/implement_rc21.py')
src=p.read_text(encoding='utf-8')
old="""        text=Path('RegionFillEngine.py').read_text(encoding='utf-8');self.assertIn('from HybridCostModel import build_cost_model',text);self.assertIn('hybrid_cost_model',text)
"""
new="""        text=Path('RegionFillEngine.py').read_text(encoding='utf-8');self.assertIn('from ExecutionCostModel import build_cost_model',text);self.assertIn('hybrid_cost_model',text)
"""
if old not in src:
    raise SystemExit('rc21 retry anchor missing in implementation script')
patched=src.replace(old,new,1)
exec(compile(patched,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
