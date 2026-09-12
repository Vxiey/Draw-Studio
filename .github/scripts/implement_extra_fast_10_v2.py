from pathlib import Path

# This runs after implement_extra_fast_10.py inside the temporary validation job.
p=Path('AdaptiveRegionHybrid.py')
text=p.read_text(encoding='utf-8')

old='''    roi_h,roi_w=target.shape
    fit_limit=max(1,min(roi_w,roi_h))
    sizes=tuple(v for v in verified if v<=fit_limit)
    pruned=tuple(v for v in verified if v>fit_limit)
    if smallest not in sizes or len(sizes)<2:
        return None,f"fewer than two verified brushes fit ROI {roi_w}x{roi_h}; pruned={pruned}"
'''
new='''    roi_h,roi_w=target.shape
    sizes,pruned=_eligible_brush_sizes_for_roi(verified,target.shape)
    if smallest not in sizes or len(sizes)<2:
        return None,f"fewer than two verified brushes fit ROI {roi_w}x{roi_h}; pruned={pruned}"
'''
if text.count(old)!=1:raise SystemExit(f'brush eligibility anchor count={text.count(old)}')
text=text.replace(old,new,1)

anchor='''def _brush_pack_candidate(comp,component_map,options,model,cancelled=lambda:False):'''
helper='''def _eligible_brush_sizes_for_roi(sizes,roi_shape):
    """Return verified sizes that can physically fit a region workspace."""
    roi_h,roi_w=map(int,roi_shape)
    fit_limit=max(1,min(roi_w,roi_h))
    normalized=tuple(sorted({max(1,int(v)) for v in sizes},reverse=True))
    eligible=tuple(v for v in normalized if v<=fit_limit)
    pruned=tuple(v for v in normalized if v>fit_limit)
    return eligible,pruned


'''
if text.count(anchor)!=1:raise SystemExit(f'brush helper anchor count={text.count(anchor)}')
text=text.replace(anchor,helper+anchor,1)

old='''    exact_candidates=[]
    for ladder in ladders:
'''
new='''    exact_candidates=[];best_residual=None
    for ladder in ladders:
'''
if text.count(old)!=1:raise SystemExit(f'residual init anchor count={text.count(old)}')
text=text.replace(old,new,1)

old='''        missing=int(np.count_nonzero(target & ~painted))
        if missing or not np.array_equal(painted,target):continue
'''
new='''        missing=int(np.count_nonzero(target & ~painted))
        best_residual=missing if best_residual is None else min(best_residual,missing)
        if missing or not np.array_equal(painted,target):continue
'''
if text.count(old)!=1:raise SystemExit(f'residual track anchor count={text.count(old)}')
text=text.replace(old,new,1)

old='''    if not exact_candidates:
        return None,f"verified brush ladders could not exactly cover ROI; eligible={sizes} pruned={pruned}"
'''
new='''    if not exact_candidates:
        residual_text="unknown" if best_residual is None else str(int(best_residual))
        return None,(f"smallest verified brush cannot exactly repair residual pixels "
                     f"(best residual={residual_text}); eligible={sizes} pruned={pruned}")
'''
if text.count(old)!=1:raise SystemExit(f'residual reason anchor count={text.count(old)}')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')

# The new pruning test should validate pruning independently from whether a tiny
# 12x12 region can be exactly tiled by an asymmetric even-sized 2 px brush.
p=Path('test_extra_fast_10_improvements_rc25.py')
t=p.read_text(encoding='utf-8')
start=t.index('    def test_brush_pack_prunes_oversized_controls_and_tests_ladders(self):')
end=t.index('\n    def test_exact_swap_replaces_lower_value_component_when_refill_cannot_fit',start)
replacement='''    def test_brush_pack_prunes_oversized_controls_and_tests_ladders(self):
        eligible,pruned=ar._eligible_brush_sizes_for_roi((28,16,8,4,2),(12,12))
        self.assertEqual(eligible,(8,4,2));self.assertEqual(pruned,(28,16))

        cmap=np.full((80,120),7,dtype=np.int32)
        h_runs=[(0,y,119,y) for y in range(80)]
        v_runs=[(x,0,x,79) for x in range(120)]
        comp=SimpleNamespace(component_id=7,color_index=0,area=120*80,bbox=(0,0,119,79),width=120,height=80,
            importance_mean=.08,importance_max=.12,edge_mean=.08,contour_mean=.08,protected_pixels=0,
            protected_ratio=0.0,horizontal_runs=h_runs,vertical_runs=v_runs)
        o=opts(30);m=build_cost_model(o,(120,80),(120,80));packed,reason=ar._brush_pack_candidate(comp,cmap,o,m)
        self.assertIsNotNone(packed,reason)
        self.assertGreaterEqual(packed['ladder_candidates_evaluated'],2)
        self.assertGreaterEqual(packed['exact_ladder_candidates'],1)
        self.assertGreaterEqual(len(set(packed['used_brush_sizes'])),2)
'''
t=t[:start]+replacement+t[end:]
p.write_text(t,encoding='utf-8')

# rc25's old test encoded a specific implementation detail (that an approximate
# preselection must over-select and then trim). Canonical TimeBudgetEngine reserve
# handling can choose the correct set immediately. Preserve the real invariant:
# the exact risk-adjusted final sequence must fit the usable path budget.
p=Path('test_extra_fast_budget_accounting_rc25.py')
t=p.read_text(encoding='utf-8')
old="        self.assertGreater(meta['budget_trimmed_components'],0)"
new="        self.assertLessEqual(meta.get('risk_adjusted_path_cost_seconds',meta['selected_path_cost_seconds']),meta['usable_path_seconds']+1e-6)"
if t.count(old)!=1:raise SystemExit(f'old trimming assertion count={t.count(old)}')
p.write_text(t.replace(old,new,1),encoding='utf-8')

print('Applied Extra Fast 10-pack v2 validation refinements.')
