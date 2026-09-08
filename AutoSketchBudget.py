"""Fit non-AI sketch detail to the configured budget, never a guessed game timer."""
import math
import time
from PIL import Image,ImageDraw
from PixelData import monochrome_strokes


def choose_sketch(original,area,options,planner,finisher,cancelled=lambda:False):
    if options.get('unlimited_time'):
        plan=planner(original,area,dict(options,sketch_detail='Detailed'),cancelled)
        plan['options']['sketch_auto_meta']={'selected_detail':'Detailed','estimated_seconds':plan['estimate'],'paths_omitted':0,'full_paths':plan['count'],'timer_source':'Unlimited'}
        return plan
    seconds=float(options.get('max_seconds',180))
    if not math.isfinite(seconds) or seconds<=0:raise ValueError('Sketch time budget must be positive and finite.')
    started=time.monotonic();trials=[]
    def remaining():return seconds*.85-(time.monotonic()-started)
    def check():
        if cancelled():raise InterruptedError()
    def done(plan,detail,trimmed,total):
        plan['options']['sketch_detail']='Auto'
        plan['options']['sketch_auto_meta']={'selected_detail':detail,'configured_seconds':seconds,
            'drawing_budget_seconds':max(0,remaining()),'estimated_seconds':plan['estimate'],
            'planning_seconds':time.monotonic()-started,'reserve_percent':15,
            'paths_omitted':trimmed,'full_paths':total,'trials':trials,
            'timer_source':'configured in app; no game timer reading'}
        return plan
    for detail in ('Detailed','Balanced','Simple'):
        check()
        plan=planner(original,area,dict(options,sketch_detail=detail),cancelled)
        trials.append({'detail':detail,'estimate':plan['estimate'],'paths':plan['count']})
        if plan['estimate']<=remaining():return done(plan,detail,0,plan['count'])
    # Every full-detail candidate exceeds the budget. Keep whole paths, with
    # the same contour priority as the Gartic engine; never interrupt a segment
    # during planning or falsify its cost. Each reduced plan is estimated again.
    full=plan
    paths=[(i,path) for i,group in enumerate(full.get('execution_groups') or []) for path in group]
    if not paths:
        if full['count']==0:return done(full,'Simple',0,0)
        raise ValueError('Auto sketch could not build continuous paths. Choose Simple or increase the time budget.')
    count=len(paths);keep=max(1,min(count-1,int(count*max(0,remaining()-3)/max(.01,full['estimate']-3)*.9)))
    for _ in range(8):
        check()
        groups=[[] for _ in full['groups']]
        raster=Image.new('RGBA',full['image'].size,'white');draw=ImageDraw.Draw(raster)
        for i,path in paths[:keep]:
            if len(path)==1:draw.point(path[0],fill='black')
            else:draw.line(path,fill='black',width=1)
            groups[i].append(path)
        raw=[[] for _ in groups]
        # Sketch plans contain exactly one active ink colour.
        active=next((i for i,g in enumerate(groups) if g),0)
        raw[active]=monochrome_strokes(raster,True,cancelled)[0]
        reduced_options=dict(full['options'],sketch_execution_groups=groups,stroke_optimizer='Off',target_stroke_count_resolved=None)
        if reduced_options.get('gartic_sketch_meta'):
            reduced_options['gartic_sketch_meta']=dict(reduced_options['gartic_sketch_meta'],execution_paths=keep)
        reduced=finisher(raster,full['fitted'],raw,reduced_options,cancelled)
        if reduced['estimate']<=remaining():return done(reduced,'Simple',count-keep,count)
        if keep<=1:break
        keep=max(1,min(keep-1,int(keep*max(0,remaining()-3)/max(.01,reduced['estimate']-3)*.85)))
    raise ValueError('Too little time remains for a safe sketch, even with Auto detail. Increase the time in the app or use a simpler image.')
