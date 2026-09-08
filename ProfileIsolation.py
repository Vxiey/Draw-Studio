"""Complete defaults reset and scoped profile control visibility."""
SETTING_NAMES=('quality', 'speed', 'precision', 'mode', 'shape_order', 'shape_model', 'max_stroke_cap', 'progressive_rendering', 'planning_watchdog', 'time_budget_mode', 'adaptive_deadline_renderer', 'deadline_safety_reserve', 'target_stroke_count', 'target_stroke_custom', 'render_style', 'draw_quality', 'human_mode', 'gpu_mode', 'gpu_vram', 'gpu_performance', 'cpu_workers', 'cpu_engine', 'ram_budget', 'ram_custom_mb', 'planning_resolution', 'resource_scheduler', 'background_fill', 'fill_engine', 'background_simplification', 'color_grouping', 'color_workflow', 'stroke_optimizer', 'adaptive_detail', 'visual_verification', 'color_rendering', 'color_fidelity', 'color_layers', 'profile_engine', 'edge_behavior', 'custom_color_workflow', 'exact_color_limit', 'tool_strategy', 'portrait_focus', 'skip_white', 'contrast', 'outline', 'brush_px', 'max_seconds', 'paint_simple', 'paint_tool', 'sketch_detail', 'read_gartic_timer', 'render_preset', 'subject_focus', 'ui_mode', 'preview_show_background', 'preview_show_fill', 'preview_show_strokes', 'preview_detail_level')

EXTRA_DEFAULTS={'subject_focus':'Off','ui_mode':'Simple','preview_show_background':True,'preview_show_fill':True,'preview_show_strokes':True}


def capture_defaults(app):
    defaults=dict(EXTRA_DEFAULTS)
    for name in SETTING_NAMES:
        var=getattr(app,name,None)
        if callable(getattr(var,'get',None)):defaults[name]=var.get()
    app._profile_defaults=defaults


def reset_settings(app):
    for name,value in getattr(app,'_profile_defaults',EXTRA_DEFAULTS).items():
        var=getattr(app,name,None)
        if callable(getattr(var,'set',None)):var.set(value)
    app.subject_region=None
    app.browser_auto_calibration_success=False
    if hasattr(app,'browser_auto_text'):app.browser_auto_text.set('Run Auto setup for this profile.')
    if hasattr(app,'subject_hint'):app.subject_hint.set('Auto: simple background or transparent PNG. Mark busy photos.')
    if hasattr(app,'preview_diagnostics_text'):app.preview_diagnostics_text.set('Preview diagnostics appear after Build preview.')
    if hasattr(app,'benchmark_suite_text'):app.benchmark_suite_text.set('Benchmark suite has not been run on this profile.')
    if hasattr(app,'_before_master_time'):del app._before_master_time
    for name in ('browser_one_click_enabled',):
        var=getattr(app,name,None)
        if var is not None:var.set(False)
    # Preview viewport and one-shot input authorization are session state.
    var=getattr(app,'preview_zoom',None)
    if var is not None:var.set(0.)
    for name in ('original_canvas','result_canvas','quantized_target_canvas','delta_e_canvas','safety_canvas','safety_debug_canvas','stroke_canvas','fill_canvas','color_canvas','coverage_canvas','accuracy_error_canvas'):
        canvas=getattr(app,name,None)
        if canvas is not None:canvas._preview_pan=(0,0)


def extra_settings(app):
    return {k:getattr(app,k).get() for k in EXTRA_DEFAULTS if hasattr(app,k)}


def restore_extra(app,data):
    values=data.get('profile_extras',{})
    if not isinstance(values,dict):return
    for name,default in EXTRA_DEFAULTS.items():
        value=values.get(name,default)
        if type(value) is not type(default):continue
        if name=='ui_mode' and value not in ('Simple','Advanced','Developer'):continue
        if name=='subject_focus' and value not in ('Off','Subject first','Subject only'):continue
        var=getattr(app,name,None)
        if var is not None:var.set(value)


def scope_visible(scope,key):
    from BrowserAutoCalibration import SUPPORTED_BROWSER_PROFILES
    return {'paint':key=='microsoft-paint','gartic':key=='gartic-phone',
            'browser':key in SUPPORTED_BROWSER_PROFILES,'nonpaint':key!='microsoft-paint'}[scope]


def register_controls(app,entries):
    app._scoped_profile_controls=[(w,scope,dict(w.pack_info())) for w,scope in entries]
    app._profile_visibility_key=None


def update_visibility(app,key):
    if getattr(app,'_profile_visibility_key',None)==key:return
    entries=getattr(app,'_scoped_profile_controls',())
    # Restore in reverse sibling order, inserting before the next packed sibling.
    for widget,scope,options in reversed(entries):
        if not scope_visible(scope,key):widget.pack_forget();continue
        if widget.winfo_manager()=='pack':continue
        siblings=list(widget.master.winfo_children());index=siblings.index(widget)
        next_widget=next((w for w in siblings[index+1:] if w.winfo_manager()=='pack'),None)
        args=dict(options)
        if next_widget is not None:args['before']=next_widget
        widget.pack(**args)
    app._profile_visibility_key=key
