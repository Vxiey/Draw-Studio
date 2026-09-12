from pathlib import Path
from textwrap import dedent


def replace(path, old, new, count=1):
    p=Path(path);text=p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'Expected rc14 patch anchor missing in {path}: {old[:160]!r}')
    p.write_text(text.replace(old,new,count),encoding='utf-8')


# RenderResume schema 3: sequence-level checkpoints use a compact canonical bitset.
replace('RenderResume.py','import hashlib\nimport json\n\nSCHEMA = 2\nSUPPORTED_SCHEMAS = (1, 2)\n',
'''import base64\nimport hashlib\nimport json\nfrom collections import Counter, defaultdict\n\nSCHEMA = 3\nSUPPORTED_SCHEMAS = (1, 2, 3)\n''')

anchor='''def _hex(value, length):\n    return isinstance(value, str) and len(value) == length and all(c in '0123456789abcdef' for c in value)\n'''
addition=dedent(r'''

def sequence_entry_key(entry) -> str:
    """Stable content key for one final execution-sequence operation.

    Runtime replanning may reorder entries, so resume identity deliberately does
    not depend on list position. Identical duplicate operations are interchangeable
    and are tracked by occurrence count in the compact canonical bitset.
    """
    if not isinstance(entry, dict):
        payload=entry
    else:
        payload={k:v for k,v in entry.items() if not str(k).startswith('_resume_')}
    raw=json.dumps(payload,sort_keys=True,separators=(',',':'),default=str,ensure_ascii=True).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()[:20]


def _sequence_catalog(plan):
    keys=sorted(sequence_entry_key(row) for row in (plan.get('execution_sequence') or ()) if isinstance(row,dict))
    digest=hashlib.sha256('|'.join(keys).encode('ascii')).hexdigest()
    return keys,digest


def sequence_context_fingerprint(plan):
    """Fingerprint everything except sequence order, which Dynamic Replanner may change."""
    clone=dict(plan)
    clone['execution_sequence']=[]
    return plan_fingerprint(clone)


def _encode_bits(flags) -> str:
    flags=list(bool(v) for v in flags);raw=bytearray((len(flags)+7)//8)
    for index,value in enumerate(flags):
        if value:raw[index//8] |= 1 << (index%8)
    return base64.b64encode(bytes(raw)).decode('ascii')


def _decode_bits(text: str, total: int):
    try:raw=base64.b64decode(str(text or '').encode('ascii'),validate=True)
    except Exception:return None
    if len(raw)!=(max(0,int(total))+7)//8:return None
    flags=[bool(raw[i//8] & (1 << (i%8))) for i in range(max(0,int(total)))]
    # Unused tail bits must stay zero so corrupted state cannot silently validate.
    if total%8 and raw:
        mask=~((1 << (total%8))-1) & 0xff
        if raw[-1] & mask:return None
    return flags


def _sequence_counts_from_bits(keys, bits):
    flags=_decode_bits(bits,len(keys))
    if flags is None:return None
    out=Counter()
    for key,done in zip(keys,flags):
        if done:out[key]+=1
    return dict(out)


def checkpoint_sequence_progress(plan, completed_counts, *, prelude_complete=True, last_entry=None):
    """Persist completed operations for progressive/Pixel Accurate execution.

    The checkpoint stores a bitset over a sorted multiset of operation hashes.
    This is both compact and order-independent, so a Dynamic Replanner reorder
    cannot invalidate safe already-completed work.
    """
    keys,catalog_fp=_sequence_catalog(plan)
    available=Counter(keys);requested=Counter()
    for key,value in dict(completed_counts or {}).items():
        if not isinstance(key,str) or len(key)!=20:continue
        try:n=max(0,int(value or 0))
        except (TypeError,ValueError,OverflowError):continue
        if key in available:requested[key]=min(n,available[key])
    seen=Counter();flags=[]
    for key in keys:
        seen[key]+=1;flags.append(seen[key] <= requested.get(key,0))
    completed=sum(flags);total=len(keys)
    out=_base(plan,0,prelude_complete=prelude_complete)
    out.update({
        'schema':SCHEMA,'plan_fingerprint':sequence_context_fingerprint(plan),
        'sequence_level':True,'sequence_total':total,'sequence_completed_count':completed,
        'sequence_catalog_fingerprint':catalog_fp,'sequence_completed_bits':_encode_bits(flags),
        'sequence_coverage_percent':round((completed/max(1,total))*100.0,3),
        'sequence_remaining_count':max(0,total-completed),
        'sequence_last_phase':str((last_entry or {}).get('phase') or '')[:80],
        'sequence_last_color_index':int((last_entry or {}).get('color_index',-1) or -1),
        'sequence_last_brush_px':max(0,int((last_entry or {}).get('brush_px',0) or 0)),
        'path_level':False,
    })
    return out

''')
replace('RenderResume.py',anchor,addition+anchor)

# Extend validation with sequence schema while preserving schemas 1/2.
replace('RenderResume.py',
'''    prelude, path_level = value.get('prelude_complete', False), value.get('path_level', False)\n    if type(prelude) is not bool or type(path_level) is not bool:\n        return None\n    out = dict(schema=schema, plan_fingerprint=fp, total_colors=total, completed_count=completed,\n               completed_keys=list(keys), next_color=completed+1 if completed<total else 0,\n               prelude_complete=prelude, active_color_number=0, active_color_index=None,\n               active_batch_key='', next_path_index=0, active_path_count=0,\n               active_items_fingerprint='', path_level=False)\n    if schema >= 2 and path_level:\n''',
'''    prelude, path_level = value.get('prelude_complete', False), value.get('path_level', False)\n    sequence_level = value.get('sequence_level', False) if schema >= 3 else False\n    if type(prelude) is not bool or type(path_level) is not bool or type(sequence_level) is not bool:\n        return None\n    out = dict(schema=schema, plan_fingerprint=fp, total_colors=total, completed_count=completed,\n               completed_keys=list(keys), next_color=completed+1 if completed<total else 0,\n               prelude_complete=prelude, active_color_number=0, active_color_index=None,\n               active_batch_key='', next_path_index=0, active_path_count=0,\n               active_items_fingerprint='', path_level=False, sequence_level=False,\n               sequence_total=0, sequence_completed_count=0, sequence_catalog_fingerprint='',\n               sequence_completed_bits='', sequence_coverage_percent=0.0, sequence_remaining_count=0,\n               sequence_last_phase='', sequence_last_color_index=-1, sequence_last_brush_px=0)\n    if schema >= 3 and sequence_level:\n        st=value.get('sequence_total');sc=value.get('sequence_completed_count');catalog=value.get('sequence_catalog_fingerprint');bits=value.get('sequence_completed_bits')\n        if type(st) is not int or type(sc) is not int or not 0 <= sc <= st or not _hex(catalog,64):return None\n        flags=_decode_bits(bits,st)\n        if flags is None or sum(flags)!=sc:return None\n        try:last_color=int(value.get('sequence_last_color_index',-1));last_brush=max(0,int(value.get('sequence_last_brush_px',0) or 0))\n        except (TypeError,ValueError,OverflowError):return None\n        out.update(sequence_level=True,sequence_total=st,sequence_completed_count=sc,\n                   sequence_catalog_fingerprint=catalog,sequence_completed_bits=str(bits),\n                   sequence_coverage_percent=round(sc/max(1,st)*100.0,3),sequence_remaining_count=max(0,st-sc),\n                   sequence_last_phase=str(value.get('sequence_last_phase') or '')[:80],\n                   sequence_last_color_index=last_color,sequence_last_brush_px=last_brush)\n        return out\n    if schema >= 2 and path_level:\n''')

# Replace resolve_resume with sequence-aware preamble; old color/path logic remains below.
replace('RenderResume.py',
'''def resolve_resume(plan,state):\n    clean=validate_progress(state);order=active_color_order(plan)\n    if not clean or (not clean['completed_count'] and not clean.get('path_level')):\n        return {'compatible':False,'completed_count':0,'total_colors':len(order),'reason':'no completed color/path progress'}\n    if plan.get('execution_sequence'):\n        return {'compatible':False,'completed_count':0,'total_colors':len(order),'reason':'progressive passes cannot resume by deterministic color path'}\n    if clean['plan_fingerprint'] != plan_fingerprint(plan):\n''',
'''def resolve_resume(plan,state):\n    clean=validate_progress(state);order=active_color_order(plan)\n    if not clean:\n        return {'compatible':False,'completed_count':0,'total_colors':len(order),'reason':'no valid render progress'}\n    if plan.get('execution_sequence'):\n        if not clean.get('sequence_level'):\n            return {'compatible':False,'completed_count':0,'total_colors':len(order),'reason':'progressive passes require a sequence checkpoint'}\n        keys,catalog_fp=_sequence_catalog(plan)\n        if clean.get('plan_fingerprint') != sequence_context_fingerprint(plan):\n            return {'compatible':False,'completed_count':0,'total_colors':len(order),'reason':'sequence render context changed'}\n        if clean.get('sequence_total') != len(keys) or clean.get('sequence_catalog_fingerprint') != catalog_fp:\n            return {'compatible':False,'completed_count':0,'total_colors':len(order),'reason':'execution sequence operations changed'}\n        completed_counts=_sequence_counts_from_bits(keys,clean.get('sequence_completed_bits'))\n        if completed_counts is None:\n            return {'compatible':False,'completed_count':0,'total_colors':len(order),'reason':'sequence checkpoint bitset is invalid'}\n        completed_sequence=sum(completed_counts.values())\n        if completed_sequence <= 0:\n            return {'compatible':False,'completed_count':0,'total_colors':len(order),'reason':'no completed sequence operations'}\n        return {\n            'compatible':True,'completed_count':0,'total_colors':len(order),'next_color':0,\n            'prelude_complete':bool(clean.get('prelude_complete')),'reason':'','path_level':False,\n            'sequence_level':True,'sequence_total':len(keys),'sequence_completed_count':completed_sequence,\n            'sequence_remaining_count':max(0,len(keys)-completed_sequence),\n            'sequence_coverage_percent':round(completed_sequence/max(1,len(keys))*100.0,3),\n            'sequence_completed_counts':completed_counts,'sequence_last_phase':clean.get('sequence_last_phase',''),\n            'sequence_last_color_index':clean.get('sequence_last_color_index',-1),\n            'sequence_last_brush_px':clean.get('sequence_last_brush_px',0),\n        }\n    if clean.get('sequence_level'):\n        return {'compatible':False,'completed_count':0,'total_colors':len(order),'reason':'sequence checkpoint cannot resume a color-batch plan'}\n    if not clean['completed_count'] and not clean.get('path_level'):\n        return {'compatible':False,'completed_count':0,'total_colors':len(order),'reason':'no completed color/path progress'}\n    if clean['plan_fingerprint'] != plan_fingerprint(plan):\n''')

# Smart Recovery: a temporarily missing/hidden browser can be checkpointed, but never auto-restarted.
replace('SmartRecovery.py',
'''        'target window geometry changed','drawing area','dpi changed','client area changed',\n        'target window no longer exists','target window is not visible','canvas moved',\n        'canvas changed','target changed','select the drawing area again','title bar/window border',\n''',
'''        'target window geometry changed','drawing area','dpi changed','client area changed',\n        'canvas moved','canvas changed','target changed','select the drawing area again','title bar/window border',\n''')
replace('SmartRecovery.py',
'''    # A bounded Stroke Delivery Verification failure means the current path was\n''',
'''    if 'target window no longer exists' in text or 'target window is not visible' in text:\n        return RecoveryDecision(True,'target temporarily unavailable',True,True)\n\n    # A bounded Stroke Delivery Verification failure means the current path was\n''')

# DrawBot: import new sequence helpers and surface resume status.
replace('DrawBot.py',
'''    from RenderResume import (resolve_resume, checkpoint_after_batch, checkpoint_before_path,\n                              checkpoint_after_path, items_fingerprint)\n''',
'''    from RenderResume import (resolve_resume, checkpoint_after_batch, checkpoint_before_path,\n                              checkpoint_after_path, checkpoint_sequence_progress, items_fingerprint,\n                              sequence_entry_key)\n''')
replace('DrawBot.py',
'''    resume_completed=int(resume_info.get('completed_count',0)) if resume_info.get('compatible') else 0\n    resume_path_level=bool(resume_info.get('compatible') and resume_info.get('path_level'))\n    resume_skip_prelude=bool(resume_info.get('compatible') and resume_info.get('prelude_complete'))\n    if resume_info.get('compatible') and (resume_completed or resume_path_level):\n        if resume_path_level:\n            report('status',f'Render resume verified: {resume_completed}/{resume_info.get("total_colors",0)} colors complete · color {resume_info.get("active_color_number")} resumes at path {int(resume_info.get("next_path_index",0))+1}/{resume_info.get("active_path_count",0)} after normal browser recalibration/preflight.')\n        else:\n            report('status',f'Render resume verified: {resume_completed}/{resume_info.get("total_colors",0)} colors already completed. Continuing from color {resume_completed+1}.')\n''',
'''    resume_completed=int(resume_info.get('completed_count',0)) if resume_info.get('compatible') else 0\n    resume_path_level=bool(resume_info.get('compatible') and resume_info.get('path_level'))\n    resume_sequence_level=bool(resume_info.get('compatible') and resume_info.get('sequence_level'))\n    resume_skip_prelude=bool(resume_info.get('compatible') and resume_info.get('prelude_complete'))\n    if resume_info.get('compatible') and (resume_completed or resume_path_level or resume_sequence_level):\n        if resume_sequence_level:\n            report('status',f'Render resume verified: {int(resume_info.get("sequence_completed_count",0)):,}/{int(resume_info.get("sequence_total",0)):,} final sequence operations already completed ({float(resume_info.get("sequence_coverage_percent",0.0)):.1f}% execution coverage). Normal target recalibration/preflight still runs before resuming.')\n        elif resume_path_level:\n            report('status',f'Render resume verified: {resume_completed}/{resume_info.get("total_colors",0)} colors complete · color {resume_info.get("active_color_number")} resumes at path {int(resume_info.get("next_path_index",0))+1}/{resume_info.get("active_path_count",0)} after normal browser recalibration/preflight.')\n        else:\n            report('status',f'Render resume verified: {resume_completed}/{resume_info.get("total_colors",0)} colors already completed. Continuing from color {resume_completed+1}.')\n''')

# Filter completed sequence operations by stable multiset counts before scheduler construction.
replace('DrawBot.py',
'''        execution_sequence=list(plan.get('execution_sequence') or [])\n        if execution_sequence:\n''',
'''        execution_sequence=list(plan.get('execution_sequence') or [])\n        sequence_completed_counts={}\n        sequence_new_completed=0\n        sequence_last_entry=None\n        if execution_sequence and resume_sequence_level:\n            sequence_completed_counts={str(k):max(0,int(v or 0)) for k,v in dict(resume_info.get('sequence_completed_counts') or {}).items()}\n            _skip=dict(sequence_completed_counts);_remaining=[];_skipped=0\n            for _entry in execution_sequence:\n                _entry_key=sequence_entry_key(_entry)\n                if _skip.get(_entry_key,0)>0:\n                    _skip[_entry_key]-=1;_skipped+=1\n                else:_remaining.append(_entry)\n            execution_sequence=_remaining\n            report('status',f'Sequence resume: skipped {_skipped:,} verified completed operation(s); {len(execution_sequence):,} remain. Dynamic Replanner may safely reorder only the remaining work.')\n        if execution_sequence:\n''')

# Stop path: atomically save all successfully completed sequence work before exiting.
replace('DrawBot.py',
'''            for _execution_index, entry in enumerate(execution_sequence):\n                if stop.is_set():\n                    raise InterruptedError()\n                pause_guard()\n''',
'''            for _execution_index, entry in enumerate(execution_sequence):\n                if stop.is_set():\n                    if checkpoint is not None and not dry_run and sequence_completed_counts:\n                        try:checkpoint(checkpoint_sequence_progress(plan,sequence_completed_counts,prelude_complete=True,last_entry=sequence_last_entry))\n                        except Exception as checkpoint_error:log_event(f'Sequence stop checkpoint skipped: {checkpoint_error!r}')\n                    raise InterruptedError()\n                pause_guard()\n''')

# Current operation is never marked complete on failure. Recoverable browser stops save prior work.
replace('DrawBot.py',
'''                _path_started=clock()\n                _pause_before_path=paused_seconds\n                draw_path_item(index,item,smart_group=True,verify_color=(index not in verified_colors and not plan['options'].get('adaptive_color_verification',False) and plan['options'].get('strict_color_verification',True)))\n                note_runtime_operation(entry.get('operation_type','stroke'),max(0.0,clock()-_path_started-(paused_seconds-_pause_before_path)))\n                if deadline_scheduler is not None:\n''',
'''                _path_started=clock()\n                _pause_before_path=paused_seconds\n                try:\n                    draw_path_item(index,item,smart_group=True,verify_color=(index not in verified_colors and not plan['options'].get('adaptive_color_verification',False) and plan['options'].get('strict_color_verification',True)))\n                except BaseException as error:\n                    if checkpoint is not None and not dry_run:\n                        try:\n                            from SmartRecovery import classify_interruption\n                            _decision=classify_interruption(error,str(plan['options'].get('profile_key') or ''))\n                            plan['options']['smart_recovery_last_decision']=_decision.as_dict()\n                            if _decision.recoverable:\n                                _progress=checkpoint_sequence_progress(plan,sequence_completed_counts,prelude_complete=True,last_entry=sequence_last_entry)\n                                checkpoint(_progress);plan['options']['smart_recovery_checkpoint']=_progress\n                                report('status',f'Smart Recovery saved {int(_progress.get("sequence_completed_count",0)):,}/{int(_progress.get("sequence_total",0)):,} completed sequence operations. Press Start again; target recalibration + visual preflight will run before resume.')\n                        except Exception as checkpoint_error:log_event(f'Sequence Smart Recovery checkpoint skipped: {checkpoint_error!r}')\n                    raise\n                note_runtime_operation(entry.get('operation_type','stroke'),max(0.0,clock()-_path_started-(paused_seconds-_pause_before_path)))\n                _entry_key=sequence_entry_key(entry)\n                sequence_completed_counts[_entry_key]=int(sequence_completed_counts.get(_entry_key,0))+1\n                sequence_new_completed+=1;sequence_last_entry=entry\n                if checkpoint is not None and not dry_run and sequence_new_completed%25==0:\n                    try:checkpoint(checkpoint_sequence_progress(plan,sequence_completed_counts,prelude_complete=True,last_entry=entry))\n                    except Exception as checkpoint_error:log_event(f'Sequence recovery checkpoint skipped: {checkpoint_error!r}')\n                if deadline_scheduler is not None:\n''')

# Save final sequence checkpoint before post-draw work; successful draw later clears it.
replace('DrawBot.py',
'''            if deadline_scheduler is not None:\n                plan['options']['deadline_runtime_meta']=deadline_scheduler.meta()\n                report('deadline_telemetry',deadline_scheduler.telemetry())\n                if deadline_scheduler.skipped:\n                    report('status',f'Deadline scheduler skipped {deadline_scheduler.skipped:,} low-value path(s); catch-up activations={deadline_scheduler.catch_up_activations}; panic activations={deadline_scheduler.panic_activations}.')\n        else:\n''',
'''            if deadline_scheduler is not None:\n                plan['options']['deadline_runtime_meta']=deadline_scheduler.meta()\n                report('deadline_telemetry',deadline_scheduler.telemetry())\n                if deadline_scheduler.skipped:\n                    report('status',f'Deadline scheduler skipped {deadline_scheduler.skipped:,} low-value path(s); catch-up activations={deadline_scheduler.catch_up_activations}; panic activations={deadline_scheduler.panic_activations}.')\n            if checkpoint is not None and not dry_run and sequence_completed_counts:\n                try:checkpoint(checkpoint_sequence_progress(plan,sequence_completed_counts,prelude_complete=True,last_entry=sequence_last_entry))\n                except Exception as checkpoint_error:log_event(f'Final sequence checkpoint skipped: {checkpoint_error!r}')\n        else:\n''')

# Diagnostics report sequence checkpoint coverage.
replace('SessionRecovery.py',
'''        "render_resume": {\n            "completed_count": int((state.get('render_resume') or {}).get('completed_count',0)),\n            "total_colors": int((state.get('render_resume') or {}).get('total_colors',0)),\n        },\n''',
'''        "render_resume": {\n            "completed_count": int((state.get('render_resume') or {}).get('completed_count',0)),\n            "total_colors": int((state.get('render_resume') or {}).get('total_colors',0)),\n            "sequence_level": bool((state.get('render_resume') or {}).get('sequence_level',False)),\n            "sequence_completed_count": int((state.get('render_resume') or {}).get('sequence_completed_count',0)),\n            "sequence_total": int((state.get('render_resume') or {}).get('sequence_total',0)),\n            "sequence_coverage_percent": float((state.get('render_resume') or {}).get('sequence_coverage_percent',0.0)),\n        },\n''')

# Release version surfaces.
replace('Version.py',"APP_VERSION = '1.0.145-rc13'","APP_VERSION = '1.0.145-rc14'")
replace('installer/ImageDrawBot.iss','#define MyAppVersion "1.0.145-rc13"','#define MyAppVersion "1.0.145-rc14"')
for test in Path('.').glob('test_*.py'):
    raw=test.read_text(encoding='utf-8')
    if '1.0.145-rc13' in raw:test.write_text(raw.replace('1.0.145-rc13','1.0.145-rc14'),encoding='utf-8')
for name in ('README.md','docs/wiki/Installation.md','docs/README.md','README-INDEX.md','docs/wiki/Home.md','docs/wiki/Updates.md'):
    p=Path(name)
    if p.exists():p.write_text(p.read_text(encoding='utf-8').replace('1.0.145-rc13','1.0.145-rc14'),encoding='utf-8')
notes='''# Image Draw Bot v1.0.145-rc14 — Resume & Checkpoints\n\n- Add schema-3 resume checkpoints for final progressive / Pixel Accurate execution sequences.\n- Track completed operations with a compact order-independent canonical bitset, so Dynamic Replanner reordering does not invalidate safe completed work.\n- Resume skips only exact operation hashes after final-plan context and sequence-multiset verification.\n- Persist sequence progress every 25 completed operations, on explicit Stop, and before exiting recoverable browser interruptions.\n- Treat a temporarily missing/hidden browser target as checkpointable, but still require explicit Start plus normal target recalibration/preflight before any mouse input resumes.\n- Keep old color-batch/path-level checkpoints fully backward compatible; changed geometry or sequence content safely rejects resume.\n'''
Path('RELEASE-NOTES-v1.0.145-rc14.md').write_text(notes,encoding='utf-8')
history='''# Image Draw Bot v1.0.145-rc14 — Resume & Checkpoints\n\n- Progressive and Pixel Accurate execution sequences can now resume safely.\n- Dynamic Replanner order changes no longer invalidate completed-work checkpoints.\n- Sequence checkpoints store compact execution coverage and remaining-work identity without restoring armed input state.\n- Temporary browser disappearance can preserve progress for the next explicitly started, recalibrated run.\n\n'''
for name in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
    p=Path(name);p.write_text(history+p.read_text(encoding='utf-8'),encoding='utf-8')

TEST=dedent(r'''\
import base64
import threading
import unittest
from pathlib import Path
from PIL import Image

from RenderResume import (checkpoint_after_batch, checkpoint_sequence_progress, resolve_resume,
                          sequence_entry_key, validate_progress)
from SmartRecovery import classify_interruption
from Version import APP_VERSION


def seq_plan(sequence=None, resume=None):
    seq=sequence or [
        {'color_index':0,'path':[(0,0),(4,0)],'phase':'major_coverage','brush_px':8,'operation_type':'stroke'},
        {'color_index':1,'path':[(0,1),(4,1)],'phase':'structure','brush_px':4,'operation_type':'stroke'},
        {'color_index':0,'path':[(1,2),(2,2)],'phase':'important_details','brush_px':2,'operation_type':'stroke'},
        {'color_index':2,'path':[(3,3),(3,4)],'phase':'accuracy','brush_px':2,'operation_type':'stroke'},
    ]
    return {
        'options':{'profile_key':'gartic-phone','profile_name':'Gartic Phone','brush_px':2,'speed':'Fast','precision':'High','drawing_mode':'Smart paths','render_resume_state':resume},
        'image':Image.new('RGB',(8,6),'white'),'fitted':(80,60),'groups':[[(0,0,4,0)],[(0,1,4,1)],[(3,3,3,4)]],
        'execution_groups':None,'execution_sequence':list(seq),'count':len(seq),
        'colors':((200,10,10),(10,200,10),(10,10,200)),
        'color_selectors':({'kind':'palette','palette_index':0},{'kind':'palette','palette_index':1},{'kind':'palette','palette_index':2}),
        'plan_area':(0,0,80,60),
    }


class Rc14SequenceResumeTests(unittest.TestCase):
    def test_sequence_checkpoint_survives_runtime_reorder(self):
        plan=seq_plan();keys=[sequence_entry_key(row) for row in plan['execution_sequence']]
        state=checkpoint_sequence_progress(plan,{keys[0]:1,keys[2]:1},last_entry=plan['execution_sequence'][2])
        reordered=seq_plan([plan['execution_sequence'][3],plan['execution_sequence'][2],plan['execution_sequence'][0],plan['execution_sequence'][1]])
        resolved=resolve_resume(reordered,state)
        self.assertTrue(resolved['compatible']);self.assertTrue(resolved['sequence_level'])
        self.assertEqual(resolved['sequence_completed_count'],2);self.assertEqual(resolved['sequence_remaining_count'],2)
        self.assertEqual(sum(resolved['sequence_completed_counts'].values()),2)

    def test_changed_sequence_operation_rejects_resume(self):
        plan=seq_plan();key=sequence_entry_key(plan['execution_sequence'][0])
        state=checkpoint_sequence_progress(plan,{key:1})
        changed=seq_plan();changed['execution_sequence'][0]=dict(changed['execution_sequence'][0],brush_px=16)
        resolved=resolve_resume(changed,state)
        self.assertFalse(resolved['compatible']);self.assertIn('sequence',resolved['reason'])

    def test_compact_bitset_and_corruption_guard(self):
        plan=seq_plan();counts={sequence_entry_key(row):1 for row in plan['execution_sequence'][:3]}
        state=checkpoint_sequence_progress(plan,counts)
        self.assertTrue(state['sequence_level']);self.assertEqual(state['sequence_completed_count'],3)
        self.assertLessEqual(len(base64.b64decode(state['sequence_completed_bits'])),1)
        broken=dict(state,sequence_completed_bits='%%%')
        self.assertIsNone(validate_progress(broken))

    def test_old_color_checkpoint_still_rejected_for_progressive_plan(self):
        base=seq_plan();base['execution_sequence']=[]
        state=checkpoint_after_batch(base,1)
        resolved=resolve_resume(seq_plan(),state)
        self.assertFalse(resolved['compatible']);self.assertIn('sequence checkpoint',resolved['reason'])

    def test_target_disappearance_is_checkpointable_but_requires_recalibration(self):
        decision=classify_interruption(ValueError('Target window no longer exists.'),'gartic-phone')
        self.assertTrue(decision.recoverable);self.assertTrue(decision.requires_recalibration);self.assertTrue(decision.full_stop)

    def test_drawbot_integrates_sequence_checkpointing(self):
        src=Path('DrawBot.py').read_text(encoding='utf-8')
        self.assertIn('checkpoint_sequence_progress',src);self.assertIn('sequence_completed_counts',src)
        self.assertIn('sequence_new_completed%25==0',src);self.assertIn('Dynamic Replanner may safely reorder only the remaining work',src)

    def test_version(self):self.assertEqual(APP_VERSION,'1.0.145-rc14')


if __name__=='__main__':unittest.main()
''')
Path('test_rc14_sequence_resume.py').write_text(TEST,encoding='utf-8')
