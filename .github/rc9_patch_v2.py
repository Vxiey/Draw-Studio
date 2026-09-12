from pathlib import Path

src=Path('.github/rc9_patch.py').read_text(encoding='utf-8')
start="old='''            \"progressive_detail_paths\": counts[\"details\"],\\n        }\\n'''"
end="text=text[:idx]+text[idx:].replace(old,new,1)"
a=src.find(start)
b=src.find(end,a)
if a<0 or b<0:
    raise SystemExit('rc9 helper metadata patch block not found')
b += len(end)
replacement='''meta_old=''' + "'''        \"progressive_phase_order\": \"large forms → important contours → details\",\\n    }'''" + '''
meta_new=''' + "'''        \"progressive_spatial_seed_paths\": int(seed_count),\\n        \"progressive_early_coverage_cells\": int(seed_cells),\\n        \"progressive_priority_model\": \"phase barriers + 4x4 spatial seeding + normalized importance\",\\n        \"progressive_phase_order\": \"large forms → important contours → details\",\\n    }'''" + '''
if meta_old not in text: raise SystemExit('rc9 final metadata anchor missing')
text=text.replace(meta_old,meta_new,1)'''
src=src[:a]+replacement+src[b:]
exec(compile(src,'.github/rc9_patch.py','exec'),{'__name__':'__main__'})
