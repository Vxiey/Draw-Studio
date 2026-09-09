from pathlib import Path

p=Path('RegionFillEngine.py')
text=p.read_text(encoding='utf-8')
old='''def _region_cost(region: dict[str, Any], options: dict[str, Any], image_size: tuple[int, int], fitted: tuple[int, int]) -> tuple[float, float]:
    from HybridCostModel import build_cost_model
    model=build_cost_model(options)
    iw, ih=max(1,int(image_size[0])),max(1,int(image_size[1]));fw,fh=max(1,int(fitted[0])),max(1,int(fitted[1]))
    sx,sy=fw/iw,fh/ih
    stroke_cost=0.0
    for raw in region.get("row_spans") or ():
        try:_y,left,right=map(int,raw)
        except Exception:continue
        stroke_cost+=model.distance_path_seconds(max(0.0,(right-left)*sx),travel_px=4.0)
    perimeter=max(1.0,float(region.get("perimeter_pixels",1) or 1))*((sx+sy)*.5)
    fill_cost=model.distance_path_seconds(perimeter,travel_px=4.0)+model.tool_change_seconds+model.fill_action_seconds+model.verification_seconds
    return max(.001,stroke_cost),max(.001,fill_cost)
'''
new='''def _region_cost(region: dict[str, Any], options: dict[str, Any], image_size: tuple[int, int], fitted: tuple[int, int]) -> tuple[float, float]:
    # Preserve the established safe-fill decision boundary on cold start.  The
    # calibrated model is allowed to change fill-vs-stroke selection only after
    # this exact profile/tool/brush/color workflow has real completed samples.
    from HybridCostModel import build_cost_model
    model = build_cost_model(options)
    if not model.calibrated:
        delivery = resolve_stroke_delivery(options, dry_run=False)
        speed_name = normalize_speed(options.get("speed", "Balanced"))
        delay = float(options.get("delay", 0.0) or 0.0)
        path_delay = max(float(delivery.min_path_delay), float(phase_delay(delay, speed_name, "path")))
        travel_delay = max(.002, float(phase_delay(delay, speed_name, "travel")))
        boundary_delay = max(.004, float(phase_delay(delay, speed_name, "boundary")))
        step = max(1.0, float(delivery.step_px))
        iw, ih = max(1, int(image_size[0])), max(1, int(image_size[1]))
        fw, fh = max(1, int(fitted[0])), max(1, int(fitted[1]))
        sx, sy = fw / iw, fh / ih
        stroke_cost = 0.0
        for raw in region.get("row_spans") or ():
            try:
                _y, left, right = map(int, raw)
            except Exception:
                continue
            length = max(0.0, (right - left) * sx)
            moves = max(1, int(ceil(length / step)))
            stroke_cost += travel_delay + moves * path_delay + delivery.press_settle + delivery.release_settle + boundary_delay
        perimeter = max(1.0, float(region.get("perimeter_pixels", 1) or 1))
        scaled_perimeter = perimeter * ((sx + sy) * .5)
        contour_moves = max(4, int(ceil(scaled_perimeter / step)))
        fill_cost = travel_delay + contour_moves * path_delay + delivery.press_settle + delivery.release_settle + boundary_delay
        fill_cost += max(.08, delivery.ui_control_delay * .45) + .24
        return max(.001, stroke_cost), max(.001, fill_cost)

    iw, ih=max(1,int(image_size[0])),max(1,int(image_size[1]));fw,fh=max(1,int(fitted[0])),max(1,int(fitted[1]))
    sx,sy=fw/iw,fh/ih
    stroke_cost=0.0
    for raw in region.get("row_spans") or ():
        try:_y,left,right=map(int,raw)
        except Exception:continue
        stroke_cost+=model.distance_path_seconds(max(0.0,(right-left)*sx),travel_px=4.0)
    perimeter=max(1.0,float(region.get("perimeter_pixels",1) or 1))*((sx+sy)*.5)
    fill_cost=model.distance_path_seconds(perimeter,travel_px=4.0)+model.tool_change_seconds+model.fill_action_seconds+model.verification_seconds
    return max(.001,stroke_cost),max(.001,fill_cost)
'''
if text.count(old)!=1:
    raise SystemExit(f'RegionFill calibrated-cost anchor mismatch: {text.count(old)}')
p.write_text(text.replace(old,new,1),encoding='utf-8')

p=Path('test_hybrid_cost_engine_v10131.py')
text=p.read_text(encoding='utf-8')
anchor='''    def test_region_fill_uses_shared_cost_model(self):
        text=Path('RegionFillEngine.py').read_text(encoding='utf-8');self.assertIn('from HybridCostModel import build_cost_model',text);self.assertIn('hybrid_cost_model',text)
'''
replacement='''    def test_region_fill_uses_shared_cost_model(self):
        text=Path('RegionFillEngine.py').read_text(encoding='utf-8');self.assertIn('from HybridCostModel import build_cost_model',text);self.assertIn('hybrid_cost_model',text)
    def test_region_fill_cold_start_preserves_legacy_cost_gate(self):
        text=Path('RegionFillEngine.py').read_text(encoding='utf-8')
        self.assertIn('if not model.calibrated:',text)
        self.assertIn('fill_cost += max(.08, delivery.ui_control_delay * .45) + .24',text)
'''
if text.count(anchor)!=1:
    raise SystemExit(f'hybrid test anchor mismatch: {text.count(anchor)}')
p.write_text(text.replace(anchor,replacement,1),encoding='utf-8')
print('HYBRID_COST_COMPAT_FIX=APPLIED')
