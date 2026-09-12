from pathlib import Path
from textwrap import dedent


def replace(path, old, new, count=1):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'Expected rc15 patch anchor missing in {path}: {old[:180]!r}')
    p.write_text(text.replace(old,new,count),encoding='utf-8')


def replace_between(path, start, end, new):
    p=Path(path); text=p.read_text(encoding='utf-8')
    a=text.find(start)
    if a<0: raise SystemExit(f'rc15 start marker missing in {path}: {start!r}')
    b=text.find(end,a+len(start))
    if b<0: raise SystemExit(f'rc15 end marker missing in {path}: {end!r}')
    p.write_text(text[:a]+new.rstrip()+"\n\n"+text[b:],encoding='utf-8')


# --- GPU memory-pressure helpers -------------------------------------------------
replace('GpuAcceleration.py',
'''def _relieve_pool_pressure(cp, budget_mb: int) -> None:\n    """Release cached CuPy blocks when the pool approaches its retention limit."""\n    used,cached=_pool_stats(cp)\n    if cached > max(96,int(budget_mb*.72)) and cached-used > 64:\n        try: cp.cuda.Stream.null.synchronize()\n        except Exception: pass\n        cp.get_default_memory_pool().free_all_blocks()\n        try: cp.get_default_pinned_memory_pool().free_all_blocks()\n        except Exception: pass\n\n\n''',
'''def _relieve_pool_pressure(cp, budget_mb: int) -> None:\n    """Release cached CuPy blocks when the pool approaches its retention limit."""\n    used,cached=_pool_stats(cp)\n    if cached > max(96,int(budget_mb*.72)) and cached-used > 64:\n        release_gpu_memory_cache(cp)\n\n\ndef release_gpu_memory_cache(cp) -> dict:\n    """Synchronize and release retained GPU/pinned blocks before a bounded retry."""\n    before_used,before_cached=_pool_stats(cp)\n    try: cp.cuda.Stream.null.synchronize()\n    except Exception: pass\n    try: cp.get_default_memory_pool().free_all_blocks()\n    except Exception: pass\n    try: cp.get_default_pinned_memory_pool().free_all_blocks()\n    except Exception: pass\n    after_used,after_cached=_pool_stats(cp)\n    return {\n        'before_used_mb':int(before_used),'before_cached_mb':int(before_cached),\n        'after_used_mb':int(after_used),'after_cached_mb':int(after_cached),\n    }\n\n\ndef is_gpu_memory_error(error: BaseException) -> bool:\n    """Recognise CUDA/OpenCL/host allocation failures without importing optional runtimes."""\n    seen=set();current=error\n    while current is not None and id(current) not in seen:\n        seen.add(id(current))\n        name=type(current).__name__.lower();message=str(current or '').lower()\n        if isinstance(current,MemoryError) or any(token in name for token in ('outofmemory','memoryallocation','memoryerror')):\n            return True\n        if any(token in message for token in (\n            'out of memory','outofmemory','cuda_error_out_of_memory','memory allocation',\n            'cl_mem_object_allocation_failure','cl_out_of_resources','failed to allocate',\n            'cannot allocate memory','insufficient memory')):\n            return True\n        current=getattr(current,'__cause__',None) or getattr(current,'__context__',None)\n    return False\n\n\ndef gpu_memory_recovery_steps(tile_rows: int, batch_size: int, *, max_retries: int=3) -> list[dict]:\n    """Return deterministic progressively smaller CUDA work units after OOM."""\n    rows=max(1,int(tile_rows or 1));batch=max(1,int(batch_size or 1));steps=[]\n    retries=max(0,min(4,int(max_retries or 0)))\n    for attempt in range(retries+1):\n        steps.append({'attempt':attempt,'tile_rows':rows,'batch_size':batch})\n        if rows>8: rows=max(8,rows//2)\n        elif rows>1: rows=max(1,rows//2)\n        if batch>256: batch=max(256,batch//2)\n        elif batch>1: batch=max(1,batch//2)\n    # Avoid pointless identical attempts when the original work unit is already tiny.\n    out=[]\n    for step in steps:\n        if not out or (step['tile_rows'],step['batch_size']) != (out[-1]['tile_rows'],out[-1]['batch_size']):\n            out.append(step)\n    return out\n\n\ndef gpu_score_tile_rows(info: AccelerationInfo, width: int, height: int, *, bytes_per_pixel: int=64, share: float=.42) -> int:\n    """Bound accuracy-score tiles to a conservative fraction of current free/budget VRAM."""\n    width=max(1,int(width));height=max(1,int(height));bpp=max(8,int(bytes_per_pixel))\n    budget=max(32,int(info.vram_budget_mb or info.free_vram_mb or 128))\n    free=max(32,int(info.free_vram_mb or budget));usable=max(16,int(min(budget,free)*max(.10,min(.70,float(share)))))\n    rows=max(8,int((usable*_MIB)//max(1,width*bpp)))\n    return max(1,min(height,1024,rows))\n\n\n''')

# --- Pixel Accurate CUDA simulation: retry smaller work units on transient OOM ---
SIMULATE = dedent(r'''\
def _simulation_attempt(cp, kernel, rects: np.ndarray, plan: SimulationPlan, width: int, height: int,
                        background_index: int, sim_host: np.ndarray, counts_host: np.ndarray,
                        *, cancelled=lambda: False) -> tuple[int,int]:
    sim_host.fill(int(background_index));counts_host.fill(0)
    launches=0;filtered_rectangles=0
    for y0 in range(0,height,plan.tile_rows):
        if cancelled():raise InterruptedError()
        y1=min(height,y0+plan.tile_rows);tile_h=y1-y0
        if len(rects):
            mask=(rects[:,3]>=y0)&(rects[:,1]<y1);tile_rects=rects[mask]
        else:tile_rects=rects
        filtered_rectangles+=len(tile_rects)
        sim_gpu=cp.asarray(sim_host[y0:y1],dtype=cp.int16)
        counts_gpu=cp.asarray(counts_host[y0:y1],dtype=cp.uint16)
        for start in range(0,len(tile_rects),plan.rectangle_batch_size):
            if cancelled():raise InterruptedError()
            batch=cp.asarray(tile_rects[start:start+plan.rectangle_batch_size],dtype=cp.int32)
            n=int(batch.shape[0])
            if n:
                total=width*tile_h;threads=256;blocks=(total+threads-1)//threads
                kernel((blocks,),(threads,),(sim_gpu,counts_gpu,np.int32(width),np.int32(y0),np.int32(tile_h),batch,np.int32(n)))
                launches+=1
            del batch
        sim_host[y0:y1]=cp.asnumpy(sim_gpu);counts_host[y0:y1]=cp.asnumpy(counts_gpu)
        del sim_gpu,counts_gpu
    cp.cuda.Stream.null.synchronize()
    return launches,filtered_rectangles


def _recovery_plan(base: SimulationPlan, height: int, rectangle_count: int, tile_rows: int, batch_size: int) -> SimulationPlan:
    rows=max(1,min(int(height),int(tile_rows)));batch=max(1,int(batch_size))
    return SimulationPlan(int(rectangle_count),rows,max(1,math.ceil(max(1,int(height))/rows)),batch,
                          max(1,math.ceil(max(1,int(rectangle_count))/batch)),base.vram_budget_mb,
                          'VRAM-recovery tiled CUDA' if rows<height or batch<max(1,rectangle_count) else base.allocation_mode)


def simulate_cuda(sequence: Sequence[dict], width: int, height: int, background_index: int, *,
                  brush_px: int = 1, gpu_mode: str = 'Auto', gpu_vram: str = 'Auto',
                  gpu_performance: str = 'High throughput', cancelled=lambda: False):
    """Return simulation arrays, shrinking CUDA work units before CPU fallback on OOM."""
    if gpu_mode=='CPU':return None
    try:
        context=_cuda_context(gpu_mode,gpu_vram,gpu_performance)
        if context is None:return None
        cp,info=context
        if not info.accelerated:return None
        rects=compile_swept_rectangles(sequence,brush_px,width,height,cancelled=cancelled)
        base_plan=_plan(info,width,height,len(rects))
        sim_host=np.full((height,width),int(background_index),dtype=np.int16)
        counts_host=np.zeros((height,width),dtype=np.uint16)
        kernel=cp.RawKernel(_KERNEL_SOURCE,'simulate_rects')
        from GpuAcceleration import gpu_memory_recovery_steps,is_gpu_memory_error,release_gpu_memory_cache
        steps=gpu_memory_recovery_steps(base_plan.tile_rows,base_plan.rectangle_batch_size,max_retries=3)
        oom_events=[];pool_releases=[]
        for n,step in enumerate(steps):
            plan=_recovery_plan(base_plan,height,len(rects),step['tile_rows'],step['batch_size'])
            try:
                launches,filtered_rectangles=_simulation_attempt(cp,kernel,rects,plan,width,height,background_index,
                                                                sim_host,counts_host,cancelled=cancelled)
                meta={
                    'simulation_backend':'cuda-cupy-tiled-raster','cuda_device':info.device,
                    'compute_capability':info.compute_capability,'gpu_performance':gpu_performance,
                    'kernel_launches':launches,'tile_filtered_rectangles':int(filtered_rectangles),**plan.as_dict(),
                    'vram_recovery_attempts':n,'vram_recovered':bool(n>0),
                    'initial_tile_rows':int(base_plan.tile_rows),'initial_rectangle_batch_size':int(base_plan.rectangle_batch_size),
                    'oom_events':tuple(oom_events),'pool_releases':tuple(pool_releases),
                }
                return sim_host,counts_host,meta
            except InterruptedError:
                raise
            except Exception as exc:
                if not is_gpu_memory_error(exc):
                    from CrashDiagnostics import log_event
                    log_event(f'CUDA stroke simulation failed; using CPU: {type(exc).__name__}: {exc}')
                    return None
                oom_events.append(f'{type(exc).__name__}: {exc}')
                from CrashDiagnostics import log_event
                if n+1>=len(steps):
                    log_event(f'CUDA stroke simulation exhausted {len(steps)} VRAM recovery attempt(s); using CPU: {type(exc).__name__}: {exc}')
                    return None
                pool_releases.append(release_gpu_memory_cache(cp))
                nxt=steps[n+1]
                log_event(f'CUDA stroke simulation VRAM pressure: retry {n+1}/{len(steps)-1} with tile_rows={nxt["tile_rows"]}, batch={nxt["batch_size"]}.')
        return None
    except InterruptedError:
        raise
    except Exception as exc:
        from CrashDiagnostics import log_event
        log_event(f'CUDA stroke simulation setup failed; using CPU: {type(exc).__name__}: {exc}')
        return None
''')
replace_between('PixelAccuracyGpu.py','def simulate_cuda(','def score_cuda_host',SIMULATE)

SCORE = dedent(r'''\
def score_cuda_host(pixel_map, simulated: np.ndarray, coverage_count: np.ndarray, background_index: int, *,
                    gpu_mode: str = 'Auto', gpu_vram: str = 'Auto', gpu_performance: str = 'High throughput',
                    cancelled=lambda: False):
    """GPU categorical error scoring in bounded row tiles with OOM tile shrink."""
    if gpu_mode=='CPU':return None
    try:
        context=_cuda_context(gpu_mode,gpu_vram,gpu_performance)
        if context is None:return None
        cp,info=context
        from GpuAcceleration import gpu_score_tile_rows,is_gpu_memory_error,release_gpu_memory_cache
        drawable_h=np.asarray(pixel_map.drawable_mask,dtype=np.bool_)
        desired_h=np.where(drawable_h,pixel_map.palette_index,int(background_index)).astype(np.int16,copy=False)
        edge_h=np.asarray(pixel_map.edge_map,dtype=np.float32)
        protected_h=np.asarray(pixel_map.protected_mask,dtype=np.bool_)&drawable_h
        vals=edge_h[drawable_h]
        edge_threshold=max(.32,float(np.percentile(vals,70.0))) if vals.size else .32
        height,width=drawable_h.shape
        initial_rows=gpu_score_tile_rows(info,width,height,bytes_per_pixel=64,share=.42)
        tile_rows=initial_rows;min_rows=max(1,min(8,height));retries=0;tiles=0
        error_host=np.zeros((height,width),dtype=np.uint8)
        totals={k:0 for k in ('evaluation','drawable','correct','covered','target_correct','edge','edge_correct',
                               'protected','protected_correct','overdraw','touched','hits','missing','wrong','spill','errors')}
        y0=0
        while y0<height:
            if cancelled():raise InterruptedError()
            y1=min(height,y0+tile_rows)
            try:
                drawable=cp.asarray(drawable_h[y0:y1]);desired=cp.asarray(desired_h[y0:y1],dtype=cp.int16)
                sim=cp.asarray(simulated[y0:y1],dtype=cp.int16);counts=cp.asarray(coverage_count[y0:y1],dtype=cp.uint16)
                coverage=counts>0;missing=drawable&~coverage;wrong=drawable&coverage&(sim!=desired)
                spill=(~drawable)&coverage&(sim!=int(background_index))
                error=cp.zeros(drawable.shape,dtype=cp.uint8);error[missing]=1;error[wrong]=2;error[spill]=3
                evaluation=drawable|coverage;correct=evaluation&(sim==desired)
                edge=cp.asarray(edge_h[y0:y1]);edge_mask=drawable&(edge>=edge_threshold)
                protected=cp.asarray(protected_h[y0:y1])
                def nz(value):return int(cp.count_nonzero(value).get())
                totals['evaluation']+=nz(evaluation);totals['drawable']+=nz(drawable);totals['correct']+=nz(correct)
                totals['covered']+=nz(drawable&coverage);totals['target_correct']+=nz(drawable&(sim==desired))
                totals['edge']+=nz(edge_mask);totals['edge_correct']+=nz(edge_mask&(sim==desired))
                totals['protected']+=nz(protected);totals['protected_correct']+=nz(protected&(sim==desired))
                totals['overdraw']+=nz(counts>1);totals['touched']+=nz(coverage)
                totals['hits']+=int(cp.sum(counts,dtype=cp.uint64).get())
                totals['missing']+=nz(missing);totals['wrong']+=nz(wrong);totals['spill']+=nz(spill);totals['errors']+=nz(error)
                error_host[y0:y1]=cp.asnumpy(error)
                del drawable,desired,sim,counts,coverage,missing,wrong,spill,error,evaluation,correct,edge,edge_mask,protected
                y0=y1;tiles+=1
            except InterruptedError:
                raise
            except Exception as exc:
                if not is_gpu_memory_error(exc):
                    from CrashDiagnostics import log_event
                    log_event(f'CUDA accuracy scoring failed; using CPU score: {type(exc).__name__}: {exc}')
                    return None
                release_gpu_memory_cache(cp);retries+=1
                if tile_rows<=min_rows or retries>4:
                    from CrashDiagnostics import log_event
                    log_event(f'CUDA accuracy scoring exhausted VRAM tile recovery; using CPU score: {type(exc).__name__}: {exc}')
                    return None
                tile_rows=max(min_rows,tile_rows//2)
                from CrashDiagnostics import log_event
                log_event(f'CUDA accuracy scoring VRAM pressure: retrying current tile with {tile_rows} row(s).')
        try:cp.cuda.Stream.null.synchronize()
        except Exception:pass
        eval_count=totals['evaluation'];drawable_count=totals['drawable'];correct_count=totals['correct']
        metrics={
            'plan_execution_accuracy_percent':round(100.0*correct_count/max(1,eval_count),4),
            'pixel_accuracy_percent':round(100.0*correct_count/max(1,eval_count),4),
            'target_color_accuracy_percent':round(100.0*totals['target_correct']/max(1,drawable_count),4),
            'coverage_percent':round(100.0*totals['covered']/max(1,drawable_count),4),
            'edge_accuracy_percent':round(100.0*totals['edge_correct']/max(1,totals['edge']),4),
            'protected_accuracy_percent':round(100.0*totals['protected_correct']/max(1,totals['protected']),4),
            'evaluation_pixels':eval_count,'drawable_pixels':drawable_count,'correct_pixels':correct_count,
            'missing_pixels':totals['missing'],'wrong_color_pixels':totals['wrong'],'spill_pixels':totals['spill'],
            'error_pixels':totals['errors'],'covered_target_pixels':totals['covered'],'edge_pixels':totals['edge'],
            'protected_pixels':totals['protected'],'touched_pixels':totals['touched'],'overdraw_pixels':totals['overdraw'],
            'total_brush_hits':totals['hits'],'mean_hits_per_touched_pixel':round(float(totals['hits']/max(1,totals['touched'])),5),
            'edge_threshold':round(edge_threshold,5),'background_index':int(background_index),
            'score_backend':'cuda-cupy-tiled-reduction' if initial_rows<height or retries else 'cuda-cupy-reduction',
            'score_cuda_device':info.device,'score_tile_rows':int(tile_rows),'score_initial_tile_rows':int(initial_rows),
            'score_tile_count':int(tiles),'score_vram_retries':int(retries),'score_vram_recovered':bool(retries>0),
        }
        return error_host,metrics
    except InterruptedError:
        raise
    except Exception as exc:
        from CrashDiagnostics import log_event
        log_event(f'CUDA accuracy scoring setup failed; using CPU score: {type(exc).__name__}: {exc}')
        return None
''')
p=Path('PixelAccuracyGpu.py');text=p.read_text(encoding='utf-8');start=text.find('def score_cuda_host')
if start<0:raise SystemExit('rc15 score function missing')
p.write_text(text[:start]+SCORE.rstrip()+"\n",encoding='utf-8')

# Universal workload router: a transient allocation failure must not quarantine a GPU for the whole process.
replace('UniversalGpuAcceleration.py',
'''def _mark_failed(route: RouteInfo, error: BaseException) -> RouteInfo:\n    message = f"{type(error).__name__}: {error}"\n    if route.backend_id != "cpu:numpy":\n        _FAILED[(route.backend_id, route.workload)] = message\n    return _cpu_route(route.workload, route.pixels, f"{route.backend_id} failed safely: {message}")\n''',
'''def _mark_failed(route: RouteInfo, error: BaseException) -> RouteInfo:\n    message = f"{type(error).__name__}: {error}"\n    transient_memory=False\n    try:\n        from GpuAcceleration import is_gpu_memory_error\n        transient_memory=is_gpu_memory_error(error)\n    except Exception:\n        transient_memory=isinstance(error,MemoryError) or 'out of memory' in str(error).lower()\n    if route.backend_id != "cpu:numpy" and not transient_memory:\n        _FAILED[(route.backend_id, route.workload)] = message\n    reason=(f"{route.backend_id} hit transient memory pressure and fell back for this call: {message}" if transient_memory else\n            f"{route.backend_id} failed safely: {message}")\n    return _cpu_route(route.workload, route.pixels, reason)\n''')

# CPU/RAM side: Auto scheduler reduces workers and chunk size if live available RAM has fallen sharply.
insert_marker='''def phase_workers(base_workers: int, phase: str, *, pixels: int, preview: bool = False) -> int:\n'''
pressure_code=dedent(r'''\
def memory_pressure_profile(allocation: dict[str, Any]) -> dict[str, Any]:
    budget=max(128,int(allocation.get('ram_budget_mb',512) or 512))
    available=allocation.get('available_ram_mb')
    try:available=int(available) if available is not None else None
    except (TypeError,ValueError,OverflowError):available=None
    if available is None:
        return {'known':False,'level':'unknown','available_ram_mb':None,'ram_budget_mb':budget,
                'worker_scale':1.0,'chunk_scale':1.0,'reason':'live available RAM unavailable'}
    ratio=available/max(1,budget)
    if available>=1536 and ratio>=1.35: level='normal';worker=1.0;chunk=1.0
    elif available>=1024 and ratio>=.95: level='elevated';worker=.80;chunk=.75
    elif available>=640 and ratio>=.55: level='high';worker=.55;chunk=.50
    else: level='critical';worker=.30;chunk=.30
    return {'known':True,'level':level,'available_ram_mb':max(0,available),'ram_budget_mb':budget,
            'available_to_budget_ratio':round(ratio,3),'worker_scale':worker,'chunk_scale':chunk,
            'reason':f'{level} RAM pressure: {max(0,available):,} MB available vs {budget:,} MB planning budget'}


def _apply_memory_pressure_workers(workers: int, pressure: dict[str,Any], *, enabled: bool=True) -> int:
    if not enabled or not pressure.get('known') or pressure.get('level')=='normal':return max(1,int(workers))
    scale=max(.20,min(1.0,float(pressure.get('worker_scale',1.0) or 1.0)))
    return max(1,min(int(workers),int(math.ceil(max(1,int(workers))*scale))))


''')
replace('ResourceScheduler.py',insert_marker,pressure_code+insert_marker)
replace('ResourceScheduler.py',
'''    base, reason = recommended_workers(allocation, mode=mode, preview=preview, recommendation=recommendation)\n    ram_mb = int(allocation.get("ram_budget_mb", 512) or 512)\n''',
'''    base, reason = recommended_workers(allocation, mode=mode, preview=preview, recommendation=recommendation)\n    pressure=memory_pressure_profile(allocation)\n    pressure_enabled=(mode!='Off')\n    adjusted_base=_apply_memory_pressure_workers(base,pressure,enabled=pressure_enabled)\n    if adjusted_base<base:\n        reason += f"; {pressure['reason']} reduced workers {base}→{adjusted_base}"\n    base=adjusted_base\n    ram_mb = int(allocation.get("ram_budget_mb", 512) or 512)\n''')
replace('ResourceScheduler.py',
'''    chunks = _chunk_hint(height, width, phases["shape_extraction"]["workers"], ram_mb)\n    phases["shape_extraction"].update(chunks)\n    return {\n''',
'''    chunks = _chunk_hint(height, width, phases["shape_extraction"]["workers"], ram_mb)\n    if pressure_enabled and pressure.get('known') and pressure.get('level')!='normal':\n        rows=max(8,int(chunks['rows_per_chunk']*float(pressure.get('chunk_scale',1.0) or 1.0)))\n        chunks={'rows_per_chunk':rows,'chunks':int(math.ceil(height/max(1,rows)))}\n    phases["shape_extraction"].update(chunks)\n    # Pixel-accuracy correction/error scoring can use the same verified GPU path on large final workloads.\n    if not preview and gpu_available and pixels>=160_000:\n        phases['correction_scoring']['backend']='GPU/CPU fallback'\n        phases['correction_scoring']['reason']='tiled GPU scoring with VRAM recovery; CPU remains authoritative fallback'\n    return {\n''')
replace('ResourceScheduler.py',
'''        "gpu_available": bool(gpu_available),\n        "phases": phases,\n''',
'''        "gpu_available": bool(gpu_available),\n        "memory_pressure": pressure,\n        "phases": phases,\n''')

# Release surfaces.
replace('Version.py',"APP_VERSION = '1.0.145-rc14'","APP_VERSION = '1.0.145-rc15'")
replace('installer/ImageDrawBot.iss','#define MyAppVersion "1.0.145-rc14"','#define MyAppVersion "1.0.145-rc15"')
for test in Path('.').glob('test_*.py'):
    raw=test.read_text(encoding='utf-8')
    if '1.0.145-rc14' in raw:test.write_text(raw.replace('1.0.145-rc14','1.0.145-rc15'),encoding='utf-8')
for name in ('README.md','docs/wiki/Installation.md','docs/README.md','README-INDEX.md','docs/wiki/Home.md','docs/wiki/Updates.md'):
    p=Path(name)
    if p.exists():p.write_text(p.read_text(encoding='utf-8').replace('1.0.145-rc14','1.0.145-rc15'),encoding='utf-8')
notes='''# Image Draw Bot v1.0.145-rc15 — CPU/GPU Performance Engine\n\n- Retry Pixel Accurate CUDA stroke simulation after transient VRAM pressure with progressively smaller row tiles and rectangle batches before CPU fallback.\n- Release retained CuPy/pinned memory between bounded OOM retries and expose recovery diagnostics.\n- Replace full-frame CUDA accuracy-score allocation with bounded row-tiled scoring that preserves the existing Pixel Accuracy metrics.\n- Shrink score tiles on transient OOM before using the deterministic CPU scorer.\n- Do not quarantine a measured GPU backend for the whole process when one workload only hits transient allocation pressure.\n- Let the Auto resource scheduler reduce CPU workers and planner chunk rows under live RAM pressure while leaving explicit Resource Scheduler = Off behavior unchanged.\n- Route large final correction-scoring phases to GPU/CPU fallback metadata when a verified GPU is available.\n'''
Path('RELEASE-NOTES-v1.0.145-rc15.md').write_text(notes,encoding='utf-8')
history='''# Image Draw Bot v1.0.145-rc15 — CPU/GPU Performance Engine\n\n- CUDA Pixel Accurate simulation now retries smaller VRAM work units before CPU fallback.\n- Accuracy scoring uses bounded GPU row tiles rather than requiring full-frame score masks.\n- Transient OOM no longer permanently quarantines an otherwise healthy GPU workload route.\n- Auto CPU scheduling reacts to live RAM pressure by reducing concurrency and chunk size.\n\n'''
for name in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
    p=Path(name);p.write_text(history+p.read_text(encoding='utf-8'),encoding='utf-8')

TEST=dedent(r'''\
import unittest
from pathlib import Path

from GpuAcceleration import (AccelerationInfo,gpu_memory_recovery_steps,gpu_score_tile_rows,
                             is_gpu_memory_error)
from ResourceScheduler import memory_pressure_profile,resolve_resource_schedule
from UniversalGpuAcceleration import RouteInfo,_mark_failed,backend_health_snapshot,reset_runtime_backend_health
from Version import APP_VERSION


class Rc15CpuGpuPerformanceTests(unittest.TestCase):
    def test_gpu_memory_error_detection_is_runtime_agnostic(self):
        self.assertTrue(is_gpu_memory_error(MemoryError('host pressure')))
        self.assertTrue(is_gpu_memory_error(RuntimeError('CUDA_ERROR_OUT_OF_MEMORY')))
        self.assertTrue(is_gpu_memory_error(RuntimeError('CL_MEM_OBJECT_ALLOCATION_FAILURE')))
        self.assertFalse(is_gpu_memory_error(RuntimeError('kernel syntax error')))

    def test_recovery_steps_shrink_tiles_and_batches(self):
        steps=gpu_memory_recovery_steps(128,8192,max_retries=3)
        self.assertGreaterEqual(len(steps),3)
        self.assertEqual((steps[0]['tile_rows'],steps[0]['batch_size']),(128,8192))
        for a,b in zip(steps,steps[1:]):
            self.assertLessEqual(b['tile_rows'],a['tile_rows']);self.assertLessEqual(b['batch_size'],a['batch_size'])
        self.assertLess(steps[-1]['tile_rows'],steps[0]['tile_rows'])

    def test_score_tiles_respect_small_vram_budget(self):
        info=AccelerationInfo('Auto','CUDA',True,'GPU',total_vram_mb=1024,free_vram_mb=180,vram_budget_mb=128)
        rows=gpu_score_tile_rows(info,5000,4000,bytes_per_pixel=64)
        self.assertGreaterEqual(rows,8);self.assertLess(rows,4000)

    def test_live_ram_pressure_reduces_auto_workers_and_chunks(self):
        allocation={'cpu_workers':'Auto','cpu_workers_resolved':16,'logical_cpus':32,'cpu_engine':'Auto',
                    'ram_budget_mb':4096,'available_ram_mb':700}
        pressure=memory_pressure_profile(allocation)
        self.assertIn(pressure['level'],('high','critical'))
        pressured=resolve_resource_schedule(allocation,mode='Auto',area=(1800,1200),gpu_mode='CPU')
        unconstrained=resolve_resource_schedule(dict(allocation,available_ram_mb=None),mode='Auto',area=(1800,1200),gpu_mode='CPU')
        self.assertLess(pressured['base_workers'],unconstrained['base_workers'])
        self.assertLessEqual(pressured['phases']['shape_extraction']['rows_per_chunk'],unconstrained['phases']['shape_extraction']['rows_per_chunk'])

    def test_scheduler_off_keeps_worker_behavior(self):
        allocation={'cpu_workers':'8','cpu_workers_resolved':8,'logical_cpus':16,'cpu_engine':'Threads',
                    'ram_budget_mb':4096,'available_ram_mb':500}
        schedule=resolve_resource_schedule(allocation,mode='Off',area=(1000,800),gpu_mode='CPU')
        self.assertEqual(schedule['base_workers'],8)

    def test_large_correction_scoring_advertises_safe_gpu_route(self):
        allocation={'cpu_workers':'Auto','cpu_workers_resolved':8,'logical_cpus':16,'cpu_engine':'Auto','ram_budget_mb':2048}
        schedule=resolve_resource_schedule(allocation,mode='Auto',area=(1200,800),gpu_mode='Auto',gpu_available=True)
        self.assertEqual(schedule['phases']['correction_scoring']['backend'],'GPU/CPU fallback')

    def test_transient_oom_does_not_quarantine_backend(self):
        reset_runtime_backend_health()
        route=RouteInfo('pixel_math','bulk_matrix','cuda:0','CUDA/CuPy','NVIDIA','GPU',True,500000)
        fallback=_mark_failed(route,RuntimeError('CUDA_ERROR_OUT_OF_MEMORY'))
        self.assertFalse(fallback.accelerated);self.assertEqual(backend_health_snapshot(),{})
        _mark_failed(route,RuntimeError('illegal memory access'))
        self.assertTrue(backend_health_snapshot())
        reset_runtime_backend_health()

    def test_pixel_accuracy_gpu_contains_bounded_retry_and_tiled_score(self):
        src=Path('PixelAccuracyGpu.py').read_text(encoding='utf-8')
        self.assertIn('gpu_memory_recovery_steps',src);self.assertIn('score_tile_rows',src)
        self.assertIn('score_vram_retries',src);self.assertNotIn('CUDA accuracy scoring exceeds allocation budget; using CPU scoring.',src)

    def test_version(self):self.assertEqual(APP_VERSION,'1.0.145-rc15')


if __name__=='__main__':unittest.main()
''')
Path('test_rc15_cpu_gpu_performance.py').write_text(TEST,encoding='utf-8')
