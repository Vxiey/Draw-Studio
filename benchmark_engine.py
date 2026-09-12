"""Reproducible CPU planner benchmark. Never sends input or reads a screen.

python benchmark_engine.py --output engine-benchmark.json
python benchmark_engine.py --source-tree ../previous-source --output baseline.json
Run references and candidates sequentially in the same environment.
"""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import time
import tracemalloc
from unittest.mock import patch


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-tree',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--repeats',type=int,default=3)
    parser.add_argument('--workers',type=int,default=1)
    args=parser.parse_args()
    if not 1<=args.repeats<=20 or not 1<=args.workers<=16:
        parser.error('repeats must be 1..20 and workers 1..16')
    root=args.source_tree.resolve()
    if not (root/'PixelStrokeEngine.py').is_file():parser.error('source tree has no PixelStrokeEngine.py')
    sys.path.insert(0,str(root))
    import numpy as np
    from PIL import Image,ImageDraw,__version__ as pillow_version
    from HybridBenchmark import CASES
    from PixelAccuratePlanner import build_pixel_map
    from PixelStrokeEngine import build_pixel_stroke_plan
    from ExecutionCostModel import build_cost_model
    from Version import APP_VERSION
    palette=((255,255,255),(0,0,0),(255,0,0),(0,0,255),(255,204,64),(54,160,92),(70,145,225),(128,128,128))
    options=dict(profile_key='isolated-benchmark',gpu_mode='CPU',speed='Balanced',precision='High',
                 delay=.006,brush_px=1,adaptive_hybrid_cost='Auto')
    def diagonal():
        im=Image.new('RGBA',(240,180),'white');d=ImageDraw.Draw(im)
        for offset in range(0,150,7):d.line((0,offset,239,min(179,offset+29)),fill='black',width=1)
        return im
    def islands():
        im=Image.new('RGBA',(120,90),'white');d=ImageDraw.Draw(im)
        for y in range(1,90,4):
            for x in range(1,120,4):d.point((x,y),fill='black' if x%8 else 'red')
        return im
    cases=tuple(CASES)+(('thin-diagonals',diagonal),('many-islands',islands))
    rows=[]
    # Freeze calibration so previous user sessions cannot contaminate a comparison.
    with patch('DrawTimeCalibration.correction_for',return_value={'samples':0,'operation_runtime':{}}):
        for name,factory in cases:
            image=factory()
            t=time.perf_counter();pm=build_pixel_map(image,palette,gpu_mode='CPU',skip_white=True)
            mapping=time.perf_counter()-t
            timings=[]
            for repeat in range(args.repeats+1):
                gc.collect();t=time.perf_counter()
                plan=build_pixel_stroke_plan(pm,len(palette),options=options,cpu_workers=args.workers)
                elapsed=time.perf_counter()-t
                if repeat==0:cold=elapsed
                else:timings.append(elapsed)
            # Measure allocations in a separate run: tracemalloc distorts timings.
            gc.collect();tracemalloc.start()
            try:
                memory_plan=build_pixel_stroke_plan(pm,len(palette),options=options,cpu_workers=args.workers)
                _,peak=tracemalloc.get_traced_memory()
                del memory_plan
            finally:tracemalloc.stop()
            rendered=Image.new('I',image.size,-1);draw=ImageDraw.Draw(rendered)
            for entry in plan['execution_sequence']:
                path=entry['path'];ci=int(entry['color_index'])
                if len(path)==1:draw.point(path[0],fill=ci)
                else:draw.line(path,fill=ci,width=1)
            actual=np.asarray(rendered);expected=np.where(pm.drawable_mask,pm.palette_index,-1)
            wrong=int(np.count_nonzero(actual!=expected))
            model=build_cost_model(options,image.size,image.size)
            breakdown=model.sequence_cost(plan['execution_sequence'],initial_brush=1)
            seconds=float(breakdown.total_seconds);switches=int(breakdown.palette_switches)
            row={'case':name,'size':image.size,'source_sha256':hashlib.sha256(image.tobytes()).hexdigest(),
                 'palette_mapping_seconds':mapping,'cold_planning_seconds':cold,
                 'warm_planning_seconds':timings,'median_planning_seconds':statistics.median(timings),
                 'peak_traced_allocation_bytes':peak,'operations':len(plan['execution_sequence']),
                 'color_selections':switches,'model_execution_seconds':seconds,
                 'actual_draw_seconds':None,'mismatched_plan_pixels':wrong,
                 'exact_palette_geometry':wrong==0,'stage_seconds':plan['metadata'].get('planning_stage_seconds')}
            rows.append(row)
            print(f'{name}: {row["median_planning_seconds"]:.4f}s; {wrong} mismatched pixels',flush=True)
    result={'schema':1,'app_version':APP_VERSION,'python':platform.python_version(),
            'platform':platform.platform(),'numpy':np.__version__,'pillow':pillow_version,
            'workers':args.workers,'repeats':args.repeats,'palette':palette,'options':options,
            'real_windows_input_verified':False,'physical_gpu_verified':False,
            'memory_scope':'tracemalloc allocation peak; excludes prebuilt PixelMap and untraced driver/RSS memory',
            'quality_scope':'1px axis/line simulation against the quantized PixelMap, not original-image perceptual fidelity',
            'cases':rows}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return 0 if all(row['exact_palette_geometry'] for row in rows) else 1

if __name__=='__main__':raise SystemExit(main())
