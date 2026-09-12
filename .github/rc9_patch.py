from pathlib import Path


def replace(path, old, new, count=1):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if old not in text: raise SystemExit(f'rc9 anchor missing in {path}: {old[:120]!r}')
    p.write_text(text.replace(old,new,count),encoding='utf-8')

p=Path('ProgressiveRenderer.py'); text=p.read_text(encoding='utf-8')
anchor='''def _importance(path: Sequence[Point], phase: str, serial: int) -> float:\n    length = _path_len(path)\n    area = _bbox_area(path)\n    if phase == "foundation":\n        return area * 0.18 + length * 1.4 - serial * 1e-6\n    if phase == "contour":\n        return length * 1.8 + area * 0.03 - serial * 1e-6\n    return length + (3.0 if len(path) == 1 else 0.0) - serial * 1e-6\n\n\n'''
insert=anchor+'''def _center(path: Sequence[Point]) -> tuple[float,float]:\n    xs=[float(p[0]) for p in path];ys=[float(p[1]) for p in path]\n    return (sum(xs)/max(1,len(xs)),sum(ys)/max(1,len(ys)))\n\n\ndef _normalized_importance(raw: float, phase: str) -> float:\n    # Monotonic bounded score for runtime deadline/replanning logic.\n    scale=80.0 if phase=='foundation' else (45.0 if phase=='contour' else 18.0)\n    value=max(0.0,float(raw))\n    return max(0.0,min(1.0,value/(value+scale)))\n\n\ndef _spatial_seed(entries: Sequence[dict], grid: int = 4) -> tuple[list[dict],int]:\n    """Put one high-value path from each occupied coarse cell before refinements."""\n    rows=list(entries or ())\n    if len(rows)<=1:return rows,len(rows)\n    centers=[row.get('_center') or _center(row['path']) for row in rows]\n    xs=[c[0] for c in centers];ys=[c[1] for c in centers]\n    xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys)\n    dx=max(1.0,xmax-xmin);dy=max(1.0,ymax-ymin);g=max(2,int(grid))\n    best={}\n    for index,(row,(x,y)) in enumerate(zip(rows,centers)):\n        cx=min(g-1,max(0,int((x-xmin)/dx*g)));cy=min(g-1,max(0,int((y-ymin)/dy*g)))\n        key=(cx,cy);old=best.get(key)\n        score=float(row.get('_progressive_score',0.0))\n        if old is None or score>float(rows[old].get('_progressive_score',0.0)):\n            best[key]=index\n    seed_indexes=set(best.values())\n    seeded=sorted((rows[i] for i in seed_indexes),key=lambda row:-float(row.get('_progressive_score',0.0)))\n    rest=sorted((row for i,row in enumerate(rows) if i not in seed_indexes),\n                key=lambda row:(-float(row.get('_progressive_score',0.0)),int(row.get('serial',0))))\n    return seeded+rest,len(seeded)\n\n\n'''
if anchor not in text: raise SystemExit('rc9 importance anchor missing')
text=text.replace(anchor,insert,1)
old='''            counts[phase] += 1\n            entries.append({\n                "color_index": int(color_index),\n                "path": path,\n                "phase": phase,\n                "phase_label": _PHASE_LABELS[phase],\n                "serial": serial,\n                "importance": _importance(path, phase, serial),\n            })\n            serial += 1\n\n    entries.sort(key=lambda item: (_PHASE_ORDER[item["phase"]], -float(item["importance"]), int(item["color_index"]), int(item["serial"])))\n    # Remove score-only field before it gets stored in the plan. Tests and logs\n    # should not depend on floating point tie-breaker values.\n    sequence = [{k: v for k, v in item.items() if k != "importance"} for item in entries]\n    return sequence, {\n'''
new='''            counts[phase] += 1\n            raw_score=_importance(path, phase, serial)\n            structural=.92 if phase=='foundation' else (.72 if phase=='contour' else .18)\n            entries.append({\n                "color_index": int(color_index),\n                "path": path,\n                "phase": phase,\n                "phase_label": _PHASE_LABELS[phase],\n                "serial": serial,\n                "importance": round(_normalized_importance(raw_score,phase),6),\n                "structural_score": structural,\n                "optional": phase=='details',\n                "_progressive_score": raw_score,\n                "_center": _center(path),\n            })\n            serial += 1\n\n    ordered=[];seed_count=0;seed_cells=0\n    for phase in ('foundation','contour','details'):\n        block=[item for item in entries if item['phase']==phase]\n        if phase in ('foundation','contour'):\n            block,seeds=_spatial_seed(block,4);seed_count+=seeds;seed_cells+=seeds\n        else:\n            block.sort(key=lambda item:(-float(item['_progressive_score']),int(item['color_index']),int(item['serial'])))\n        ordered.extend(block)\n    # Keep normalized importance/structure metadata for the runtime scheduler,\n    # but remove planner-only score/center fields.\n    sequence=[{k:v for k,v in item.items() if k not in ('_progressive_score','_center')} for item in ordered]\n    return sequence, {\n'''
if old not in text: raise SystemExit('rc9 build sequence anchor missing')
text=text.replace(old,new,1)
old='''            "progressive_detail_paths": counts["details"],\n        }\n'''
# only replace final metadata occurrence; disabled metadata does not have phase_order after this block
new='''            "progressive_detail_paths": counts["details"],\n            "progressive_spatial_seed_paths": int(seed_count),\n            "progressive_early_coverage_cells": int(seed_cells),\n            "progressive_priority_model": "phase barriers + 4x4 spatial seeding + normalized importance",\n        }\n'''
# The first occurrence is in disabled return and lacks variables; target last occurrence by rsplit.
idx=text.rfind(old)
if idx<0: raise SystemExit('rc9 metadata anchor missing')
text=text[:idx]+text[idx:].replace(old,new,1)
p.write_text(text,encoding='utf-8')

Path('test_rc9_progressive_drawing.py').write_text(r'''import unittest
from ProgressiveRenderer import build_progressive_sequence
from Version import APP_VERSION

class Rc9ProgressiveDrawingTests(unittest.TestCase):
    def test_spatial_seeding_spreads_foundation_early(self):
        groups=[[
            ((0,0),(30,0)),((100,0),(130,0)),((0,100),(30,100)),((100,100),(130,100)),
            ((1,2),(70,2)),
        ]]
        hints=[['foundation']*5]
        seq,meta=build_progressive_sequence(groups,phase_hints=hints,enabled=True)
        self.assertGreaterEqual(meta['progressive_spatial_seed_paths'],4)
        prefix=seq[:meta['progressive_spatial_seed_paths']]
        centers=[((p['path'][0][0]+p['path'][-1][0])/2,(p['path'][0][1]+p['path'][-1][1])/2) for p in prefix]
        self.assertGreaterEqual(len({(int(x>=65),int(y>=50)) for x,y in centers}),3)

    def test_phase_barriers_and_geometry_are_preserved(self):
        groups=[[((0,0),(50,0)),((10,10),(10,40)),((3,3),)]]
        hints=[['foundation','contour','details']]
        seq,meta=build_progressive_sequence(groups,phase_hints=hints,enabled=True)
        self.assertEqual([e['phase'] for e in seq],['foundation','contour','details'])
        self.assertEqual(sorted(tuple(e['path']) for e in seq),sorted(groups[0]))

    def test_runtime_priority_metadata_is_bounded(self):
        seq,_=build_progressive_sequence([[((0,0),(100,0)),((1,1),)]],phase_hints=[['foundation','details']],enabled=True)
        for e in seq:
            self.assertGreaterEqual(e['importance'],0.0);self.assertLessEqual(e['importance'],1.0)
            self.assertIn('structural_score',e);self.assertIn('optional',e)

    def test_version(self):self.assertEqual(APP_VERSION,'1.0.145-rc9')

if __name__=='__main__':unittest.main()
''',encoding='utf-8')

replace('Version.py',"APP_VERSION = '1.0.145-rc8'","APP_VERSION = '1.0.145-rc9'")
replace('installer/ImageDrawBot.iss','#define MyAppVersion "1.0.145-rc8"','#define MyAppVersion "1.0.145-rc9"')
readme=Path('README.md');readme.write_text(readme.read_text(encoding='utf-8').replace('1.0.145-rc8','1.0.145-rc9'),encoding='utf-8')
for test in Path('.').glob('test_*.py'):
    if test.name=='test_rc9_progressive_drawing.py':continue
    t=test.read_text(encoding='utf-8')
    if '1.0.145-rc8' in t:test.write_text(t.replace('1.0.145-rc8','1.0.145-rc9'),encoding='utf-8')
history=Path('VERSION-HISTORY.md');h=history.read_text(encoding='utf-8')
heading='# Image Draw Bot v1.0.145-rc9 — Progressive Drawing 2.0'
if heading not in h:
    history.write_text(heading+'\n\n- Progressive passes now seed broad forms and contours across a bounded 4x4 spatial grid before local refinement.\n- The renderer keeps phase barriers and source geometry unchanged while making the whole subject recognizable earlier.\n- Progressive entries now carry bounded importance, structural score and optional-detail metadata for runtime deadline decisions.\n\n'+h,encoding='utf-8')
Path('RELEASE-NOTES-v1.0.145-rc9.md').write_text('''# Image Draw Bot v1.0.145-rc9 — Progressive Drawing 2.0\n\n- Spread foundation and contour work across the image early using bounded 4x4 spatial seeding.\n- Preserve all existing safe paths and phase barriers; this release changes execution priority, not geometry.\n- Carry normalized importance/structure metadata into the final execution sequence so deadline handling can prioritize meaningful detail.\n- Keep small-detail refinement after the recognizable whole has been established.\n''',encoding='utf-8')
print('rc9 patch applied')
