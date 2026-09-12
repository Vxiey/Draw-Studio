from pathlib import Path


def replace(path, old, new, count=1):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'rc8 anchor missing in {path}: {old[:140]!r}')
    p.write_text(text.replace(old,new,count),encoding='utf-8')

# DeadlineScheduler: add bounded runtime reordering of the remaining safe sequence.
p=Path('DeadlineScheduler.py'); text=p.read_text(encoding='utf-8')
old='''        self._recovered_from_catchup = 0\n        self.current_phase = ""\n'''
new='''        self._recovered_from_catchup = 0\n        self.replan_count = 0\n        self.reordered_paths = 0\n        self.replan_rejected_switch_cost = 0\n        self._last_replan_sample = -1\n        self._last_replan_mode = NORMAL\n        self._last_replan_scale = 1.0\n        self.current_phase = ""\n'''
if old not in text: raise SystemExit('rc8 scheduler init anchor missing')
text=text.replace(old,new,1)
anchor='''    def prediction_interval(self):\n        """Heuristic variability envelope, not a statistical confidence interval."""\n'''
methods='''    @staticmethod\n    def _transition_count(entries) -> int:\n        """Count colour/brush transitions without assigning any UI timing."""\n        transitions=0;last_color=object();last_brush=object();started=False\n        for raw in entries or ():\n            entry=dict(raw)\n            if str(entry.get("operation_type") or "stroke") != "stroke":\n                continue\n            color=entry.get("color_index");brush=entry.get("brush_px")\n            if started and (color!=last_color or brush!=last_brush):transitions+=1\n            last_color=color;last_brush=brush;started=True\n        return transitions\n\n    def _replan_priority(self, entry, original_index: int):\n        phase=self._phase(entry);importance=self._score(entry,"importance",.5)\n        structural=self._score(entry,"structural_score",0.0);optional=bool(entry.get("optional"))\n        adjusted=self._cost(entry)*self._runtime_scale(self._op_type(entry))\n        if self.mode == PANIC:\n            if phase in ("major_coverage","structure"):tier=0\n            elif phase == "important_details" and importance >= RUNTIME_POLICY["panic_detail_min_importance"]:tier=1\n            else:tier=2\n            value=max(structural,importance)\n        else:\n            value=max(structural*.92,importance)\n            tier=0 if (not optional and value>=.70) else (1 if not optional else 2)\n        # Original index is the final tie-breaker, keeping the sort deterministic.\n        return (tier,-round(value,6),round(adjusted,6),original_index)\n\n    def replan_remaining(self, remaining, *, force: bool = False):\n        """Reorder only already-safe remaining paths inside contiguous phase barriers.\n\n        Geometry, colour, brush width and phase membership are immutable. Non-stroke\n        operations are hard barriers. A candidate is rejected when it would increase\n        colour/brush transitions, so catch-up cannot become slower by UI thrashing.\n        """\n        rows=[dict(entry) for entry in (remaining or ())]\n        if len(rows)<2 or self.budget_seconds is None or self.mode == NORMAL:return rows\n        scale=self._runtime_scale()\n        if not force:\n            if self._global_samples < 2:return rows\n            sample_gap=self._global_samples-self._last_replan_sample\n            scale_delta=abs(scale-self._last_replan_scale)\n            if self.mode==self._last_replan_mode and sample_gap<2 and scale_delta<.12:return rows\n        output=[];moved=0;rejected=0;start=0\n        while start<len(rows):\n            first=rows[start];op=self._op_type(first);phase=self._phase(first)\n            if op!='stroke':\n                output.append(first);start+=1;continue\n            end=start+1\n            while end<len(rows) and self._op_type(rows[end])=='stroke' and self._phase(rows[end])==phase:\n                end+=1\n            block=rows[start:end]\n            indexed=list(enumerate(block))\n            ranked=sorted(indexed,key=lambda pair:self._replan_priority(pair[1],pair[0]))\n            candidate=[entry for _idx,entry in ranked]\n            if [idx for idx,_entry in ranked] != list(range(len(block))):\n                if self._transition_count(candidate) <= self._transition_count(block):\n                    moved += sum(1 for pos,(idx,_entry) in enumerate(ranked) if pos!=idx)\n                    block=candidate\n                else:\n                    rejected+=1\n            output.extend(block);start=end\n        self._last_replan_sample=self._global_samples\n        self._last_replan_mode=self.mode\n        self._last_replan_scale=scale\n        if moved:\n            self.replan_count+=1;self.reordered_paths+=moved\n        self.replan_rejected_switch_cost+=rejected\n        return output\n\n'''+anchor
if anchor not in text: raise SystemExit('rc8 scheduler method anchor missing')
text=text.replace(anchor,methods,1)
old='''            "recovered_from_catchup": int(self._recovered_from_catchup),\n        }\n'''
new='''            "recovered_from_catchup": int(self._recovered_from_catchup),\n            "dynamic_replans": int(self.replan_count),\n            "reordered_remaining_paths": int(self.reordered_paths),\n            "replans_rejected_switch_cost": int(self.replan_rejected_switch_cost),\n            "last_replan_mode": self._last_replan_mode,\n        }\n'''
if old not in text: raise SystemExit('rc8 telemetry anchor missing')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')

# DrawBot: use the replanner after each measured path without replacing geometry.
p=Path('DrawBot.py'); text=p.read_text(encoding='utf-8')
old="        execution_sequence=plan.get('execution_sequence') or []\n"
new="        execution_sequence=list(plan.get('execution_sequence') or [])\n"
if old not in text: raise SystemExit('rc8 execution sequence anchor missing')
text=text.replace(old,new,1)
old='''            for entry in execution_sequence:\n                if stop.is_set():\n'''
new='''            for _execution_index, entry in enumerate(execution_sequence):\n                if stop.is_set():\n'''
if old not in text: raise SystemExit('rc8 execution loop anchor missing')
text=text.replace(old,new,1)
old='''                if deadline_scheduler is not None:\n                    deadline_scheduler.after(entry,excluded_seconds=paused_seconds-_pause_before_entry)\n                    _now=clock()\n'''
new='''                if deadline_scheduler is not None:\n                    deadline_scheduler.after(entry,excluded_seconds=paused_seconds-_pause_before_entry)\n                    _tail=list(execution_sequence[_execution_index+1:])\n                    _replanned=deadline_scheduler.replan_remaining(_tail)\n                    if _replanned != _tail:\n                        execution_sequence[_execution_index+1:]=_replanned\n                        report('status',f'Dynamic Replanner: {deadline_scheduler.mode} reordered remaining safe paths without changing geometry.')\n                    _now=clock()\n'''
if old not in text: raise SystemExit('rc8 scheduler after anchor missing')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')

# Focused regression tests.
Path('test_rc8_dynamic_replanner.py').write_text(r'''import unittest
from pathlib import Path
from DeadlineScheduler import DeadlineScheduler, NORMAL, CATCH_UP, PANIC
from Version import APP_VERSION


def entry(i, *, phase='structure', importance=.5, structural=.5, optional=False, color=0, brush=4, cost=1.0):
    return {'source_index':i,'path':((i,0),(i+1,0)),'deadline_phase':phase,
            'estimated_cost_seconds':cost,'importance':importance,'structural_score':structural,
            'optional':optional,'color_index':color,'brush_px':brush,'operation_type':'stroke'}

class Rc8DynamicReplannerTests(unittest.TestCase):
    def scheduler(self, seq):
        return DeadlineScheduler(seq,start_time=0.0,budget_seconds=20.0,clock=lambda:0.0)

    def test_normal_mode_preserves_planned_order(self):
        seq=[entry(0,importance=.1),entry(1,importance=.9)]
        s=self.scheduler(seq)
        self.assertEqual([x['source_index'] for x in s.replan_remaining(seq,force=True)],[0,1])
        self.assertEqual(s.mode,NORMAL)

    def test_catchup_prioritizes_high_value_inside_phase_only(self):
        seq=[entry(0,importance=.2,structural=.2),entry(1,importance=.95,structural=.9),entry(2,importance=.6,structural=.6)]
        s=self.scheduler(seq);s.mode=CATCH_UP;s._global_samples=3
        out=s.replan_remaining(seq,force=True)
        self.assertEqual(out[0]['source_index'],1)
        self.assertEqual(sorted(x['source_index'] for x in out),[0,1,2])
        self.assertGreaterEqual(s.replan_count,1)

    def test_phase_barriers_are_never_crossed(self):
        seq=[entry(0,phase='structure',importance=.1),entry(1,phase='important_details',importance=.1),entry(2,phase='structure',importance=.99)]
        s=self.scheduler(seq);s.mode=PANIC;s._global_samples=4
        out=s.replan_remaining(seq,force=True)
        self.assertEqual([x['deadline_phase'] for x in out],['structure','important_details','structure'])
        self.assertEqual([x['source_index'] for x in out],[0,1,2])

    def test_replan_never_increases_color_brush_transitions(self):
        seq=[entry(0,importance=.2,color=0,brush=4),entry(1,importance=.95,color=1,brush=8),entry(2,importance=.8,color=0,brush=4)]
        s=self.scheduler(seq);s.mode=CATCH_UP;s._global_samples=3
        before=s._transition_count(seq);out=s.replan_remaining(seq,force=True)
        self.assertLessEqual(s._transition_count(out),before)
        self.assertEqual(sorted(tuple(x['path']) for x in out),sorted(tuple(x['path']) for x in seq))

    def test_drawbot_has_runtime_replan_hook(self):
        src=Path('DrawBot.py').read_text(encoding='utf-8')
        self.assertIn('enumerate(execution_sequence)',src)
        self.assertIn('deadline_scheduler.replan_remaining(_tail)',src)

    def test_version(self):
        self.assertEqual(APP_VERSION,'1.0.145-rc8')

if __name__=='__main__':unittest.main()
''',encoding='utf-8')

# Release metadata.
replace('Version.py',"APP_VERSION = '1.0.145-rc6'","APP_VERSION = '1.0.145-rc8'")
replace('installer/ImageDrawBot.iss','#define MyAppVersion "1.0.145-rc6"','#define MyAppVersion "1.0.145-rc8"')
readme=Path('README.md'); r=readme.read_text(encoding='utf-8'); readme.write_text(r.replace('1.0.145-rc6','1.0.145-rc8'),encoding='utf-8')
for test in Path('.').glob('test_*.py'):
    if test.name=='test_rc8_dynamic_replanner.py':continue
    t=test.read_text(encoding='utf-8')
    if '1.0.145-rc6' in t:
        test.write_text(t.replace('1.0.145-rc6','1.0.145-rc8'),encoding='utf-8')
history=Path('VERSION-HISTORY.md'); h=history.read_text(encoding='utf-8')
heading='# Image Draw Bot v1.0.145-rc8 — Dynamic Replanner'
if heading not in h:
    h=heading+'\n\n- Added live runtime replanning on top of the existing DeadlineScheduler.\n- CATCH_UP/PANIC can reorder only remaining already-safe stroke paths inside contiguous phase barriers; geometry, colors and brush widths are never rewritten.\n- Non-stroke operations remain hard barriers and candidate replans are rejected if they increase color/brush transitions.\n- Replanning is throttled by measured runtime samples and exposed through deadline telemetry.\n\n'+h
    history.write_text(h,encoding='utf-8')
Path('RELEASE-NOTES-v1.0.145-rc8.md').write_text('''# Image Draw Bot v1.0.145-rc8 — Dynamic Replanner\n\n- Extend the live DeadlineScheduler with bounded runtime replanning.\n- Reorder remaining safe paths only when measured execution enters CATCH_UP or PANIC.\n- Preserve phase barriers, non-stroke operation barriers, geometry, colors and brush widths.\n- Reject a candidate replan if it would increase color/brush transition count.\n- Add runtime telemetry for replans, reordered paths and rejected switch-heavy reorderings.\n''',encoding='utf-8')
print('rc8 patch applied')
