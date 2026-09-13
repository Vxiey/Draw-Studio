from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def replace(path,old,new,count=1):
    p=ROOT/path;text=p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'rc27 anchor missing in {path}: {old[:120]!r}')
    p.write_text(text.replace(old,new,count),encoding='utf-8')

# Auto Brush: Gartic public/requested width is a five-level scale only.
replace(Path('AutoBrushWidth.py'),
"""    cap=6 if str(profile_key or '')=='microsoft-paint' else 8
    base=max(1,min(cap,int(base)))
""",
"""    key=str(profile_key or '').lower()
    if key=='microsoft-paint':cap=6
    elif key in ('gartic-phone','gartic-io'):cap=5
    else:cap=8
    base=max(1,min(cap,int(base)))
""")

# Profile isolation/persistence for Gartic-only opacity.
replace(Path('ProfileIsolation.py'),"'outline', 'brush_px', 'max_seconds'","'outline', 'brush_px', 'gartic_opacity', 'max_seconds'")

# UI: keep row handle so Gartic-only controls can be hidden as a complete row.
replace(Path('StudioUI.py'),
"""        tooltip(widget, explanation)
        return widget

    def numeric_row""",
"""        tooltip(widget, explanation)
        widget._setting_row = row
        return widget

    def numeric_row""")
replace(Path('StudioUI.py'),
"""    numeric_row(step4, 'Brush width (px)', a.brush_px, 'Auto chooses a safe pixel baseline from the image/canvas; manual 1–50 px remains available.', width=84)
    focus_menu = setting_row(step4, 'Subject focus', a.subject_focus,
""",
"""    numeric_row(step4, 'Brush width', a.brush_px, 'Auto chooses from Gartic levels 1–5. Other profiles keep their normal pixel-width range.', width=84)
    a.gartic_opacity_menu = setting_row(step4, 'Gartic opacity', a.gartic_opacity,
        ['Auto','10%','20%','30%','40%','50%','60%','70%','80%','90%','100%'],
        'Auto analyzes edges, color complexity and smooth shading. Low opacity is used only when it can improve tonal likeness.', width=118)
    a.gartic_opacity_row = getattr(a.gartic_opacity_menu, '_setting_row', a.gartic_opacity_menu)
    focus_menu = setting_row(step4, 'Subject focus', a.subject_focus,
""")
replace(Path('StudioUI.py'),
"""        (a.gartic_setup_button,'gartic'),(timer_switch,'gartic')])""",
"""        (a.gartic_setup_button,'gartic'),(timer_switch,'gartic'),(a.gartic_opacity_row,'gartic')])""")

# Runtime state + options validation + browser preflight opacity plan.
replace(Path('DrawBot.py'),
"""        self.brush_px = tk.StringVar(value='Auto')
        self.max_seconds = tk.StringVar(value='180')
""",
"""        self.brush_px = tk.StringVar(value='Auto')
        self.gartic_opacity = tk.StringVar(value='Auto')
        self.max_seconds = tk.StringVar(value='180')
""")
replace(Path('DrawBot.py'),
"""        if (brush is not None and not 1<=brush<=50) or not 5<=limit<=3600:
            raise ValueError('Brush width: Auto or 1–50 px. Time limit: 5–3600 seconds.')
        auto_brush_width_meta=None
""",
"""        _profile_key_for_brush=PROFILES[self.game.get()][0]
        _brush_limit=5 if _profile_key_for_brush in ('gartic-phone','gartic-io') else 50
        if (brush is not None and not 1<=brush<=_brush_limit) or not 5<=limit<=3600:
            _label='Gartic level 1–5' if _brush_limit==5 else '1–50 px'
            raise ValueError(f'Brush width: Auto or {_label}. Time limit: 5–3600 seconds.')
        auto_brush_width_meta=None
""")
replace(Path('DrawBot.py'),
"""'brush_px':brush,'brush_px_requested':brush_raw,'auto_brush_width_meta':auto_brush_width_meta,'canvas_edge_verification':'Auto'""",
"""'brush_px':brush,'brush_px_requested':brush_raw,'auto_brush_width_meta':auto_brush_width_meta,'gartic_opacity':getattr(getattr(self,'gartic_opacity',None),'get',lambda:'Auto')(),'canvas_edge_verification':'Auto'""")
replace(Path('DrawBot.py'),
"""                    options['canvas_guard_brush_px']=int(brush_plan.safe_guard_px)
                    log_event(f\"Automatic browser brush preflight: profile={profile_key} requested={brush_plan.requested_px}px effective={brush_plan.effective_px}px target={brush_plan.target_position!r} selected={brush_plan.selected_index!r} confidence={brush_plan.confidence:.3f} guard={brush_plan.safe_guard_px}px.\")
""",
"""                    options['canvas_guard_brush_px']=int(brush_plan.safe_guard_px)
                    _brush_meta=options['browser_brush_plan']
                    _level_note=(f\" level={_brush_meta.get('effective_level')}\" if _brush_meta.get('effective_level') else '')
                    log_event(f\"Automatic browser brush preflight: profile={profile_key} requested={brush_plan.requested_px}{_level_note} physical={brush_plan.effective_px}px target={brush_plan.target_position!r} selected={brush_plan.selected_index!r} confidence={brush_plan.confidence:.3f} guard={brush_plan.safe_guard_px}px.\")
                    if profile_key in ('gartic-phone','gartic-io'):
                        from GarticOpacity import plan_gartic_opacity
                        opacity_plan=plan_gartic_opacity(profile_key,shot,tuple(current_client),
                            canvas_box=(x,y,x+w,y+h),source_image=self.original,
                            requested=options.get('gartic_opacity','Auto'),draw_quality=options.get('draw_quality',''),
                            render_style=options.get('render_style',''),drawing_mode=options.get('drawing_mode',''),
                            outline=bool(options.get('outline')))
                        options['gartic_opacity_plan']=opacity_plan.as_dict()
                        options['gartic_opacity_percent']=int(opacity_plan.selected_percent)
                        log_event(f\"Gartic opacity preflight: requested={opacity_plan.requested} selected={opacity_plan.selected_percent}% confidence={opacity_plan.confidence:.3f} target={opacity_plan.target_position!r} reason={opacity_plan.reason}.\")
""")

# Final-canvas scoring is useful after every completed real draw, not just when
# Auto Tuner happened to be active.
replace(Path('DrawBot.py'),
"""        tuner=plan['options'].get('auto_tuner_meta') or {}
        if dry_run or not isinstance(tuner,dict) or not tuner.get('active') or not hasattr(mouse,'snapshot_canvas'):
            return None
""",
"""        tuner=plan['options'].get('auto_tuner_meta') or {}
        if dry_run or not hasattr(mouse,'snapshot_canvas'):
            return None
""")
replace(Path('DrawBot.py'),
"""                report('status',f\"Real result verification: trust {trust}, Visual {float(visual or 0):.1f}%, Actual coverage {float(cov or 0):.1f}%, Actual vs simulated {float(sim or 0):.1f}%.\")
""",
"""                report('status',f\"Drawing Accuracy Score {float(visual or 0):.1f}/100 · trust {trust} · coverage {float(cov or 0):.1f}% · actual vs simulated {float(sim or 0):.1f}%.\")
""")

# Apply a verified reduced-opacity target before brush selection. 100% is
# intentionally no-op so an unverified slider never receives guessed input.
replace(Path('DrawBot.py'),
"""        brush_plan=plan['options'].get('browser_brush_plan') or {}
        if brush_plan and not resume_skip_prelude:
""",
"""        opacity_plan=plan['options'].get('gartic_opacity_plan') or {}
        if opacity_plan and not resume_skip_prelude and int(opacity_plan.get('selected_percent',100) or 100)<100:
            opacity_target=opacity_plan.get('target_position')
            if opacity_target:
                _opacity_started=clock();_opacity_percent=int(opacity_plan.get('selected_percent',100) or 100)
                click_ui_control(tuple(map(int,opacity_target)),f'Gartic opacity {_opacity_percent}%')
                _opacity_seconds=max(0.0,clock()-_opacity_started)
                note_runtime_operation('opacity_change',_opacity_seconds)
                plan['options']['gartic_opacity_runtime_meta']={'applied':True,'percent':_opacity_percent,'seconds':round(_opacity_seconds,5)}
            else:
                plan['options']['gartic_opacity_runtime_meta']={'applied':False,'percent':100,'seconds':0.0,'reason':'slider not verified'}
        brush_plan=plan['options'].get('browser_brush_plan') or {}
        if brush_plan and not resume_skip_prelude:
""")

# Persist evidence-rich completed drawing report after normal clean real draws.
replace(Path('DrawBot.py'),
"""            except Exception as estimate_error:
                log_event(f'Draw-time calibration save skipped: {estimate_error!r}')
        if (not dry_run) and (not plan['options'].get('correction_only_retry')) and speed_measure_completed and execution_measure_started is not None:
            try:
                from AutoTunerFeedback import record_completed_feedback
""",
"""            except Exception as estimate_error:
                log_event(f'Draw-time calibration save skipped: {estimate_error!r}')
        if (not dry_run) and (not plan['options'].get('correction_only_retry')) and speed_measure_completed and execution_measure_started is not None:
            try:
                from CompletedDrawingAnalysis import record_completed_drawing
                _actual_analysis=max(.001,(execution_measure_completed_at or clock())-execution_measure_started)
                analysis_meta=record_completed_drawing(plan,_actual_analysis,completed_paths=done)
                plan['options']['completed_drawing_analysis_meta']=analysis_meta
                _score=analysis_meta.get('drawing_accuracy_score_0_100')
                _score_label='unavailable' if _score is None else f'{float(_score):.1f}/100'
                log_event(f\"Completed Drawing Analysis saved: accuracy={_score_label} efficiency={analysis_meta.get('efficiency_score_0_100')} recommendations={len(analysis_meta.get('recommendations') or ())} file={analysis_meta.get('latest_json_path')}.\")
                report('status',f\"Completed Drawing Analysis: accuracy {_score_label} · {len(analysis_meta.get('recommendations') or ())} optimization suggestion(s) saved.\")
            except Exception as analysis_error:
                log_event(f'Completed Drawing Analysis save skipped: {analysis_error!r}')
        if (not dry_run) and (not plan['options'].get('correction_only_retry')) and speed_measure_completed and execution_measure_started is not None:
            try:
                from AutoTunerFeedback import record_completed_feedback
""")

# PyInstaller includes new runtime modules.
replace(Path('build_exe.py'),
"""        '--hidden-import', 'BrowserBrushSize',
        '--hidden-import', 'BrowserToolLayout',
""",
"""        '--hidden-import', 'BrowserBrushSize',
        '--hidden-import', 'GarticOpacity',
        '--hidden-import', 'CompletedDrawingAnalysis',
        '--hidden-import', 'BrowserToolLayout',
""")

# Version surfaces. Keep README download links on the latest published release.
replace(Path('Version.py'),"APP_VERSION = '1.0.145-rc26'","APP_VERSION = '1.0.145-rc27'")
replace(Path('installer/ImageDrawBot.iss'),'#define MyAppVersion "1.0.145-rc26"','#define MyAppVersion "1.0.145-rc27"')
for p in ROOT.glob('test_*.py'):
    text=p.read_text(encoding='utf-8')
    if '1.0.145-rc26' in text:
        p.write_text(text.replace('1.0.145-rc26','1.0.145-rc27'),encoding='utf-8')

notes="""# Image Draw Bot v1.0.145-rc27 — Completed Drawing Intelligence\n\n- Save a profile-local Completed Drawing Analysis after clean real draws with predicted vs actual time, typed operation costs, brush decisions and prioritized optimization suggestions.\n- Show a real **Drawing Accuracy Score 0–100** from the final canvas snapshot versus the original source whenever safe screenshot capture is available, independent of Auto Tuner state.\n- Keep screenshots and source pixels in memory only; completed reports persist metrics, not image data.\n- Expose Gartic brush selection as the real five-level **1–5** control while keeping calibrated physical footprints separate for CanvasGuard and stroke simulation.\n- Add Gartic opacity **Auto / 10–100%**. Auto analyzes edge density, color complexity and smooth tonal variation; reduced opacity is fail-closed unless the slider is visually verified.\n- Time opacity changes as real UI operations so ETA/optimization work can learn their cost.\n"""
(ROOT/'RELEASE-NOTES-v1.0.145-rc27.md').write_text(notes,encoding='utf-8')

history=notes.replace('# Image Draw Bot v1.0.145-rc27 — Completed Drawing Intelligence\n\n','')
for name in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
    p=ROOT/name;p.write_text('# Image Draw Bot v1.0.145-rc27 — Completed Drawing Intelligence\n\n'+history+'\n'+p.read_text(encoding='utf-8'),encoding='utf-8')

# Regression tests dedicated to the new evidence loop.
test=r'''import tempfile,unittest\nfrom pathlib import Path\nfrom PIL import Image,ImageDraw\nimport CompletedDrawingAnalysis as CDA\nfrom GarticOpacity import choose_opacity_percent,validate_opacity,plan_gartic_opacity\nfrom AutoBrushWidth import resolve_brush_width\nfrom BrowserBrushSize import plan_browser_brush_size\nfrom Version import APP_VERSION\n\nclass Rc27Tests(unittest.TestCase):\n    def test_version(self):self.assertEqual(APP_VERSION,'1.0.145-rc27')\n    def test_gartic_auto_brush_never_exceeds_level_five(self):\n        im=Image.new('RGB',(3000,1800),'white')\n        self.assertLessEqual(resolve_brush_width(im,target_size=im.size,profile_key='gartic-phone',render_preset='Extra fast').brush_px,5)\n    def test_opacity_validation(self):\n        self.assertEqual(validate_opacity('30%'),'30%')\n        with self.assertRaises(ValueError):validate_opacity('25%')\n    def test_flat_image_prefers_opaque(self):\n        im=Image.new('RGB',(400,300),'white');ImageDraw.Draw(im).rectangle((40,40,360,260),fill='red')\n        self.assertEqual(choose_opacity_percent(im,requested='Auto')['selected_percent'],100)\n    def test_completed_analysis_keeps_accuracy_components(self):\n        plan={'options':{'profile_key':'gartic-phone','profile_name':'Gartic Phone','post_draw_accuracy_meta':{'available':True,'trusted':True,'feedback_trust':'high','visual_accuracy_percent':91.5,'source_pixel_accuracy_percent':90,'perceptual_color_accuracy_percent':92,'luminance_accuracy_percent':94,'hue_accuracy_percent':91,'edge_accuracy_percent':87,'actual_coverage_percent':98,'unexpected_ink_percent':1.0},'runtime_operation_timing':{'stroke':{'count':10,'total_seconds':5,'average_seconds':.5}},'browser_brush_plan':{'requested_level':3,'effective_level':3,'nominal_sizes':[2,4,8]}},'draw_time_estimate':{'projected_seconds':12},'estimate':12}\n        r=CDA.build_completed_drawing_report(plan,10,completed_paths=10)\n        self.assertEqual(r['drawing_accuracy_score_0_100'],91.5);self.assertEqual(r['accuracy']['edge_accuracy_percent'],87.0)\n        self.assertIn('recommendations',r)\n    def test_source_contains_universal_scoring_and_completed_analysis(self):\n        src=Path('DrawBot.py').read_text(encoding='utf-8')\n        self.assertIn("if dry_run or not hasattr(mouse,'snapshot_canvas')",src)\n        self.assertIn('from CompletedDrawingAnalysis import record_completed_drawing',src)\n        self.assertIn("note_runtime_operation('opacity_change'",src)\n\nif __name__=='__main__':unittest.main()\n'''.replace('\\n','\n')
(ROOT/'test_rc27_completed_drawing_intelligence.py').write_text(test,encoding='utf-8')
