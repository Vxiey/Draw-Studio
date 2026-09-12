from pathlib import Path
import runpy

# Apply the main root-cause patch first.
runpy.run_path('.github/scripts/fix_extra_fast_region_quality.py', run_name='__main__')

p=Path('DrawBot.py')
text=p.read_text(encoding='utf-8')
old="""    if (options.get('extra_fast') and options.get('extra_fast_v2')
            and not options.get('_adaptive_hybrid_inner')
            and not (options.get('paint_current_color') or options.get('outline') or options.get('erase_mode'))):
        from AdaptiveRegionHybrid import build_adaptive_hybrid_plan
"""
new="""    if (options.get('extra_fast') and options.get('extra_fast_v2')
            and not options.get('_adaptive_hybrid_inner')
            and not (options.get('paint_current_color') or options.get('outline') or options.get('erase_mode'))
            # A legacy/manual profile can claim Fill capability without carrying
            # executable tool actions. Preserve the proven ExtraFast2 Fill route
            # for that incomplete metadata case; regional hybrid owns all no-Fill
            # runs (the user's failing Gartic case) and fully calibrated Fill runs.
            and (not options.get('fill_tool_available') or bool(options.get('fill_tool_actions')))):
        from AdaptiveRegionHybrid import build_adaptive_hybrid_plan
"""
if text.count(old)!=1:
    raise SystemExit(f'patched Extra Fast route anchor count={text.count(old)}')
p.write_text(text.replace(old,new),encoding='utf-8')
print('Extra Fast v2 compatibility guard applied.')
