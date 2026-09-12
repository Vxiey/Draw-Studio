from pathlib import Path


def replace(path, old, new, count=1):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'rc11 anchor missing in {path}: {old[:140]!r}')
    p.write_text(text.replace(old,new,count),encoding='utf-8')

smart=r'''"""Smart Color Engine for Image Draw Bot.

Pure planning helpers used by AdaptivePaletteFidelity. The engine raises the
priority of small but locally dominant / perceptually unique colours without
allowing them to overwhelm broad coverage. It also provides a conservative
marginal-value gate so colour-switch cost can influence when palette growth
stops instead of merely changing a diagnostic number.
"""
from __future__ import annotations

from math import hypot
from typing import Sequence

from ColorFidelity import delta_e2000

Segment = tuple[int,int,int,int]


def _stroke_mass(stroke) -> float:
    try:
        x1,y1,x2,y2=map(float,stroke)
        return max(1.0,hypot(x2-x1,y2-y1))
    except Exception:
        return 1.0


def _clamp(value: float, lo: float=0.0, hi: float=1.0) -> float:
    return max(lo,min(hi,float(value)))


def smart_color_weights(groups: Sequence[Sequence[Segment]], palette_rgb: Sequence[Sequence[int]],
                        base_weights: Sequence[float], *, fidelity: str='Faithful', grid: int=4):
    """Return importance-adjusted colour weights plus deterministic diagnostics.

    The multiplier is driven by local cell dominance, spatial locality and
    perceptual uniqueness. Total weight is re-normalized afterwards so this is
    a redistribution of importance, not an artificial increase in image mass.
    """
    palette=[tuple(map(int,row[:3])) for row in palette_rgb]
    n=max(len(groups),len(base_weights),len(palette))
    base=[float(base_weights[i]) if i<len(base_weights) else 0.0 for i in range(n)]
    active=[i for i in range(min(len(groups),len(palette))) if base[i]>0 and groups[i]]
    empty_meta={
        'smart_color_engine':'Smart Color Engine v1','smart_color_enabled':False,
        'smart_color_grid':f'{max(2,int(grid))}x{max(2,int(grid))}',
        'smart_color_anchor_indexes':(), 'smart_color_unique_indexes':(),
        'smart_color_priority_multipliers':{}, 'smart_color_max_priority_multiplier':1.0,
    }
    if not active:
        return base,empty_meta

    records=[];xs=[];ys=[]
    for ci in active:
        for stroke in groups[ci]:
            try:
                x1,y1,x2,y2=map(float,stroke)
            except Exception:
                continue
            mass=_stroke_mass(stroke);cx=(x1+x2)*.5;cy=(y1+y2)*.5
            records.append((ci,cx,cy,mass));xs.append(cx);ys.append(cy)
    if not records:
        return base,empty_meta

    g=max(2,min(8,int(grid)))
    xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys)
    dx=max(1.0,xmax-xmin);dy=max(1.0,ymax-ymin)
    cells={}
    for ci,x,y,mass in records:
        gx=min(g-1,max(0,int((x-xmin)/dx*g)))
        gy=min(g-1,max(0,int((y-ymin)/dy*g)))
        bucket=cells.setdefault((gx,gy),{})
        bucket[ci]=bucket.get(ci,0.0)+mass

    max_base=max(base[i] for i in active) or 1.0
    coefficients={
        'Fast':(.10,.06,.05,1.28),
        'Balanced':(.26,.14,.09,1.65),
        'Faithful':(.44,.23,.14,2.00),
        'Exact':(.50,.28,.16,2.20),
    }
    local_k,unique_k,scarce_k,cap=coefficients.get(str(fidelity),coefficients['Faithful'])
    multipliers={};anchor_scores={};unique_indexes=[]
    for ci in active:
        shares=[];dominant_cells=0;occupied=0
        for bucket in cells.values():
            if ci not in bucket:continue
            occupied+=1;total=sum(bucket.values()) or 1.0
            share=bucket[ci]/total;shares.append(share)
            top=max(bucket,key=lambda k:(bucket[k],-k))
            if top==ci:dominant_cells+=1
        local_dom=max(shares or [0.0])
        locality=1.0-_clamp((occupied-1)/max(1.0,g*g*.50))
        cell_authority=_clamp(dominant_cells/max(1,occupied))
        nearest=100.0
        for other in active:
            if other==ci:continue
            nearest=min(nearest,float(delta_e2000(palette[ci],palette[other])))
        if len(active)<=1:nearest=100.0
        uniqueness=_clamp((nearest-2.5)/22.0)
        if nearest>=12.0:unique_indexes.append(ci)
        scarcity=1.0-_clamp(base[ci]/max_base)
        local_signal=local_dom*(.55+.45*locality)
        multiplier=1.0 + local_k*local_signal + unique_k*uniqueness + scarce_k*scarcity*local_dom
        multiplier += .08*cell_authority*locality if fidelity!='Fast' else 0.0
        multiplier=max(.80,min(cap,multiplier));multipliers[ci]=multiplier
        anchor_scores[ci]=local_signal*.58+uniqueness*.27+cell_authority*.15

    raw=[0.0]*n
    for i in range(n):raw[i]=base[i]*multipliers.get(i,1.0)
    base_total=sum(base[i] for i in active) or 1.0
    raw_total=sum(raw[i] for i in active) or base_total
    scale=base_total/raw_total
    adjusted=[raw[i]*scale for i in range(n)]

    # Only a bounded set is eligible for guaranteed local-priority anchoring.
    # Broad dominant colours are already protected by the normal hue/tone logic;
    # these anchors are mainly for locally authoritative accents/details.
    limit=max(2,min(8,(len(active)+3)//4))
    candidates=[i for i in active if anchor_scores[i]>=.42]
    candidates.sort(key=lambda i:(-anchor_scores[i],-multipliers[i],i))
    anchors=tuple(candidates[:limit])
    meta={
        'smart_color_engine':'Smart Color Engine v1','smart_color_enabled':True,
        'smart_color_grid':f'{g}x{g}','smart_color_anchor_indexes':anchors,
        'smart_color_unique_indexes':tuple(sorted(unique_indexes)),
        'smart_color_priority_multipliers':{str(i):round(multipliers[i],4) for i in active},
        'smart_color_max_priority_multiplier':round(max(multipliers.values()),4),
        'smart_color_weight_normalization':round(scale,6),
    }
    return adjusted,meta


def should_keep_color_candidate(relative_gain: float, posterization_score: float, fidelity: str,
                                color_switch_seconds: float) -> bool:
    """Conservative marginal-value gate for adding another palette colour."""
    fidelity=str(fidelity or 'Faithful')
    force_risk={'Fast':.62,'Balanced':.52,'Faithful':.38,'Exact':.31}.get(fidelity,.38)
    if float(posterization_score)>=force_risk:
        return True
    base_threshold={'Fast':.0100,'Balanced':.0045,'Faithful':.0018,'Exact':.00045}.get(fidelity,.0018)
    cost_scale=max(.30,min(5.0,float(color_switch_seconds or .065)/.065))
    return max(0.0,float(relative_gain)) >= base_threshold*cost_scale
'''
Path('SmartColorEngine.py').write_text(smart,encoding='utf-8')

test=r'''import unittest
from SmartColorEngine import smart_color_weights, should_keep_color_candidate
from AdaptivePaletteFidelity import select_adaptive_palette
from Version import APP_VERSION

class Rc11SmartColorEngineTests(unittest.TestCase):
    def test_local_unique_accent_receives_relative_priority(self):
        palette=[(120,120,120),(150,150,150),(0,220,230)]
        groups=[
            [(0,0,120,0),(0,25,120,25),(0,50,120,50),(0,75,120,75)],
            [(0,90,90,90),(0,100,90,100)],
            [(102,102,112,102),(102,104,112,104)],
        ]
        base=[480.0,180.0,20.0]
        adjusted,meta=smart_color_weights(groups,palette,base,fidelity='Faithful')
        self.assertTrue(meta['smart_color_enabled'])
        self.assertIn(2,meta['smart_color_unique_indexes'])
        self.assertGreater(adjusted[2]/base[2],adjusted[0]/base[0])

    def test_switch_cost_can_stop_low_value_palette_growth(self):
        self.assertTrue(should_keep_color_candidate(.0002,.55,'Faithful',.30))
        self.assertFalse(should_keep_color_candidate(.0002,.30,'Faithful',.30))
        self.assertTrue(should_keep_color_candidate(.02,.30,'Faithful',.30))

    def test_selector_exports_smart_color_diagnostics(self):
        palette=[(20,20,20),(100,100,100),(240,240,240),(220,30,30),(30,80,220),(20,190,90)]
        groups=[[(0,i*10,40+i*3,i*10)] for i in range(len(palette))]
        _keep,_mapping,meta=select_adaptive_palette(groups,palette,4,fidelity='Faithful',color_switch_seconds=.12)
        self.assertEqual(meta['smart_color_engine'],'Smart Color Engine v1')
        self.assertIn('smart_color_anchor_indexes',meta)
        self.assertAlmostEqual(meta['smart_color_switch_cost_seconds'],.12,places=5)

    def test_version(self):
        self.assertEqual(APP_VERSION,'1.0.145-rc11')

if __name__=='__main__':unittest.main()
'''
Path('test_rc11_smart_color_engine.py').write_text(test,encoding='utf-8')

p=Path('AdaptivePaletteFidelity.py');text=p.read_text(encoding='utf-8')
text=text.replace('from RegionAwareQuantization import region_detail_anchor_candidates\n',
                  'from RegionAwareQuantization import region_detail_anchor_candidates\nfrom SmartColorEngine import smart_color_weights, should_keep_color_candidate\n',1)
old='''def _base_anchors(groups: Sequence[Sequence[Segment]], palette: Sequence[tuple[int,int,int]],\n                  active: Sequence[int], weights: Sequence[float], cap: int,\n                  fidelity: str) -> list[int]:'''
new='''def _base_anchors(groups: Sequence[Sequence[Segment]], palette: Sequence[tuple[int,int,int]],\n                  active: Sequence[int], weights: Sequence[float], cap: int,\n                  fidelity: str, priority_anchors: Sequence[int]=()) -> list[int]:'''
if old not in text:raise SystemExit('rc11 base anchors signature missing')
text=text.replace(old,new,1)
old='''    for i in dominant_anchors:\n        add(i)\n    add(darkest); add(brightest)\n\n    # Preserve a luminance ladder'''
new='''    for i in dominant_anchors:\n        add(i)\n    add(darkest); add(brightest)\n    # Smart Color anchors come after broad hue/extreme protection so a local\n    # accent cannot evict the image's essential hue structure.\n    for i in priority_anchors:\n        add(int(i))\n\n    # Preserve a luminance ladder'''
if old not in text:raise SystemExit('rc11 anchor insertion missing')
text=text.replace(old,new,1)
old='''    palette=[tuple(map(int,r[:3])) for r in palette_rgb]\n    weights=group_weights(groups)\n    active=[i for i,w in enumerate(weights) if w>0 and i<len(palette)]'''
new='''    palette=[tuple(map(int,r[:3])) for r in palette_rgb]\n    base_weights=group_weights(groups)\n    weights,smart_meta=smart_color_weights(groups,palette,base_weights,fidelity=fidelity)\n    active=[i for i,w in enumerate(weights) if w>0 and i<len(palette)]'''
if old not in text:raise SystemExit('rc11 selector weight anchor missing')
text=text.replace(old,new,1)
old="""    if not active:\n        return [],{}, {'active_colors_before':0,'active_colors_after':0,'max_colors':int(max_colors),'posterization_risk':'LOW','palette_coverage_percent':100.0}\n"""
new="""    if not active:\n        meta={'active_colors_before':0,'active_colors_after':0,'max_colors':int(max_colors),'posterization_risk':'LOW','palette_coverage_percent':100.0}\n        meta.update(smart_meta);meta['smart_color_switch_cost_seconds']=round(max(.005,float(color_switch_seconds)),6)\n        return [],{},meta\n"""
if old not in text:raise SystemExit('rc11 empty selector anchor missing')
text=text.replace(old,new,1)
old="""        meta.update({'active_colors_before':len(active),'active_colors_after':len(active),'max_colors':int(max_colors),'selected_colors':len(active),'visual_gain_per_color_switch':0.0,\n                     'kept_color_indexes':tuple(map(int,active)),\n"""
new="""        meta.update(smart_meta)\n        meta.update({'active_colors_before':len(active),'active_colors_after':len(active),'max_colors':int(max_colors),'selected_colors':len(active),'visual_gain_per_color_switch':0.0,\n                     'smart_color_switch_cost_seconds':round(max(.005,float(color_switch_seconds)),6),\n                     'smart_color_cost_stop':False,\n                     'kept_color_indexes':tuple(map(int,active)),\n"""
if old not in text:raise SystemExit('rc11 active meta anchor missing')
text=text.replace(old,new,1)
old="keep=_base_anchors(groups,palette,active,weights,cap,fidelity)"
new="keep=_base_anchors(groups,palette,active,weights,cap,fidelity,smart_meta.get('smart_color_anchor_indexes',()))"
if old not in text:raise SystemExit('rc11 base anchor call missing')
text=text.replace(old,new,1)
old='''    last_gain=0.0\n    # Faithful/Exact demand a better reduced palette before stopping.\n    target_risk={"Fast":.52,"Balanced":.40,"Faithful":.28,"Exact":.20}[fidelity]\n    while len(keep)<cap and metrics['posterization_score']>target_risk:\n        best=None\n        current_error={i:de*weights[i] for i,de,_w in errors}\n        for candidate in active:\n            if candidate in keep: continue\n            trial_keep=keep+[candidate]\n            _m,_e=_map_indices(active,trial_keep,palette,weights,fidelity)\n            new_total=sum(de*w for _i,de,w in _e)\n            old_total=sum(current_error.values())\n            gain=max(0.0,old_total-new_total)/max(.005,float(color_switch_seconds))\n            if best is None or gain>best[0]:\n                best=(gain,candidate,_m,_e)\n        if not best:break\n        last_gain,candidate,mapping,errors=best\n        keep.append(candidate)\n        metrics=palette_quality_metrics(active,keep,palette,weights,mapping,errors,fidelity=fidelity,max_colors=cap)\n'''
new='''    last_gain=0.0;last_relative_gain=0.0;cost_stop=False\n    # Faithful/Exact demand a better reduced palette before stopping.\n    target_risk={"Fast":.52,"Balanced":.40,"Faithful":.28,"Exact":.20}[fidelity]\n    while len(keep)<cap and metrics['posterization_score']>target_risk:\n        best=None\n        current_error={i:de*weights[i] for i,de,_w in errors}\n        old_total=sum(current_error.values())\n        for candidate in active:\n            if candidate in keep: continue\n            trial_keep=keep+[candidate]\n            _m,_e=_map_indices(active,trial_keep,palette,weights,fidelity)\n            new_total=sum(de*w for _i,de,w in _e)\n            delta=max(0.0,old_total-new_total)\n            relative=delta/max(1e-9,old_total)\n            gain=delta/max(.005,float(color_switch_seconds))\n            if best is None or gain>best[0]:\n                best=(gain,relative,candidate,_m,_e)\n        if not best:break\n        candidate_gain,candidate_relative,candidate,candidate_mapping,candidate_errors=best\n        if not should_keep_color_candidate(candidate_relative,float(metrics['posterization_score']),fidelity,color_switch_seconds):\n            cost_stop=True;break\n        last_gain,last_relative_gain=candidate_gain,candidate_relative\n        mapping,errors=candidate_mapping,candidate_errors\n        keep.append(candidate)\n        metrics=palette_quality_metrics(active,keep,palette,weights,mapping,errors,fidelity=fidelity,max_colors=cap)\n'''
if old not in text:raise SystemExit('rc11 palette loop anchor missing')
text=text.replace(old,new,1)
old="""    metrics.update({\n        'active_colors_before':len(active),'active_colors_after':len(keep),\n"""
new="""    metrics.update(smart_meta)\n    metrics.update({\n        'active_colors_before':len(active),'active_colors_after':len(keep),\n        'smart_color_switch_cost_seconds':round(max(.005,float(color_switch_seconds)),6),\n        'smart_color_last_relative_gain_percent':round(float(last_relative_gain)*100.0,4),\n        'smart_color_cost_stop':bool(cost_stop),\n"""
if old not in text:raise SystemExit('rc11 final meta anchor missing')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')

replace('Version.py',"APP_VERSION = '1.0.145-rc10'","APP_VERSION = '1.0.145-rc11'")
replace('installer/ImageDrawBot.iss','#define MyAppVersion "1.0.145-rc10"','#define MyAppVersion "1.0.145-rc11"')
readme=Path('README.md');readme.write_text(readme.read_text(encoding='utf-8').replace('1.0.145-rc10','1.0.145-rc11'),encoding='utf-8')
for testfile in Path('.').glob('test_*.py'):
    if testfile.name=='test_rc11_smart_color_engine.py':continue
    t=testfile.read_text(encoding='utf-8')
    if '1.0.145-rc10' in t:testfile.write_text(t.replace('1.0.145-rc10','1.0.145-rc11'),encoding='utf-8')
history=Path('VERSION-HISTORY.md');h=history.read_text(encoding='utf-8')
heading='# Image Draw Bot v1.0.145-rc11 — Smart Color Engine'
if heading not in h:
    history.write_text(heading+'\n\n- Added local spatial dominance and perceptual uniqueness to palette importance scoring.\n- Small locally authoritative accents can keep a palette slot without overpowering broad coverage.\n- Colour-switch cost now participates in the stop decision for low-value extra palette colours.\n- Existing dominant-hue, tone-ladder and region-detail protections remain authoritative.\n\n'+h,encoding='utf-8')
Path('RELEASE-NOTES-v1.0.145-rc11.md').write_text('''# Image Draw Bot v1.0.145-rc11 — Smart Color Engine\n\n- Add Smart Color Engine importance weights from local spatial dominance, locality and perceptual uniqueness.\n- Preserve locally important accent/detail colours after dominant hue and luminance-extreme protection.\n- Make colour-switch cost affect whether another low-value palette colour is worth adding.\n- Export Smart Color diagnostics for selected anchors, unique colours, priority multipliers and cost stops.\n- Keep existing region-aware quantization, dominant-hue preservation and perceptual palette mapping intact.\n''',encoding='utf-8')
print('rc11 patch applied')
