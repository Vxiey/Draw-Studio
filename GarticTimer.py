"""Read the pictured Gartic pie timer. A single frame never implies seconds.

Pure image geometry plus several timed observations. No OCR, AI or input.
"""
import math
import time
import numpy as np


def _components(mask):
    # Row-run union-find avoids visiting every canvas pixel in Python.
    parent=[];boxes=[];previous=[]
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for y,row in enumerate(mask):
        changes=np.flatnonzero(np.diff(np.r_[False,row,False].astype(np.int8)))
        current=[];j=0
        for left,right in zip(changes[::2],changes[1::2]):
            left=int(left);right=int(right);i=len(parent);parent.append(i);boxes.append((left,y,right,y+1));current.append((left,right,i))
            while j<len(previous) and previous[j][1]<left:j+=1
            k=j
            while k<len(previous) and previous[k][0]<=right:
                a=root(i);b=root(previous[k][2])
                if a!=b:parent[b]=a
                k+=1
        previous=current
    out={}
    for i,(l,t,r,b) in enumerate(boxes):
        key=root(i)
        if key in out:
            a,c,d,e=out[key];out[key]=(min(a,l),min(c,t),max(d,r),max(e,b))
        else:out[key]=(l,t,r,b)
    return list(out.values())


def read_ring(image,box):
    a=np.asarray(image.convert('RGB'));h,w=a.shape[:2]
    l,t,r,b=map(float,box);cx=(l+r-1)/2;cy=(t+b-1)/2;radius=(r-l+b-t)/4
    angles=np.arange(720)*2*np.pi/720
    def samples(scale):
        xs=np.rint(cx+radius*scale*np.sin(angles)).astype(int)
        ys=np.rint(cy-radius*scale*np.cos(angles)).astype(int)
        if xs.min()<0 or ys.min()<0 or xs.max()>=w or ys.max()>=h:raise ValueError('Timer ring is clipped.')
        return a[ys,xs].astype(float)
    ring=samples(.93);pale=(ring[:,0]>150)&(ring[:,1]>90)&(ring[:,2]>110)
    inside=samples(.80);dark=(inside[:,0]>inside[:,1]*1.35)&(inside[:,1]<100)
    if pale.mean()<.80 or dark.mean()<.72:raise ValueError('Timer ring appearance does not match Gartic.')
    fractions=[]
    for scale in (.35,.5,.65):
        pixels=samples(scale);white=np.min(pixels,axis=1)>215
        # A pie is one contiguous wedge, not digits, a clock hand or a logo.
        transitions=np.count_nonzero(white!=np.roll(white,1))
        if transitions>6:raise ValueError('Timer interior is not a single pie wedge.')
        fractions.append(float(white.mean()))
    if max(fractions)-min(fractions)>.055:raise ValueError('Timer fill is inconsistent across the circle.')
    return {'fraction':float(np.median(fractions)),'box':tuple(map(int,box)),
            'confidence':float(min(pale.mean(),dark.mean()))}


def find_timer(image,canvas_box=None,cancelled=lambda:False):
    if cancelled():raise InterruptedError()
    rgb=image.convert('RGB');scale=min(1,960/rgb.width)
    small=rgb.resize((max(1,round(rgb.width*scale)),max(1,round(rgb.height*scale))))
    a=np.asarray(small);mask=(a[:,:,0]>150)&(a[:,:,1]>90)&(a[:,:,2]>110)
    found=[]
    for l,t,r,b in _components(mask):
        if cancelled():raise InterruptedError()
        w=r-l;h=b-t
        if not (18<=w<=160 and 18<=h<=160 and .88<=w/h<=1.12):continue
        box=tuple(round(v/scale) for v in (l,t,r,b));cx=(box[0]+box[2])/2;cy=(box[1]+box[3])/2
        if canvas_box and canvas_box[0]<=cx<=canvas_box[2] and canvas_box[1]<=cy<=canvas_box[3]:continue
        try:found.append(read_ring(rgb,box))
        except ValueError:continue
    if len(found)!=1:raise ValueError('Gartic timer not uniquely visible. Show the whole round timer or turn off Read Gartic timer and set time manually.')
    return found[0]


def estimate_remaining(observations):
    if len(observations)<4:raise ValueError('More timer observations are required.')
    a=np.asarray(observations,dtype=float);t=a[:,0]-a[0,0];f=a[:,1]
    if not np.isfinite(a).all() or np.any(np.diff(t)<=0) or np.any((f<0)|(f>1)):raise ValueError('Invalid timer observations.')
    duration=t[-1]
    if duration<4 or f[0]-f[-1]<.018:raise ValueError('Timer is static or changing too slowly to estimate seconds. Try again or set time manually.')
    if np.any(np.diff(f)>.006):raise ValueError('Timer reset or increased; no drawing time was inferred.')
    slope,intercept=np.polyfit(t,f,1);rate=-float(slope)
    if rate<=0 or np.max(np.abs(f-(intercept+slope*t)))>.009:raise ValueError('Timer movement is inconsistent; no drawing time was inferred.')
    if f[-1]<=.01:raise ValueError('Gartic timer is nearly empty.')
    seconds=float(f[-1]/rate)
    # Angular sampling and short observation windows limit precision. Use the
    # conservative bound for drawing, and label the central result approximate.
    error=.006
    safe=max(0,float((f[-1]-error)/(rate+2*error/duration)))
    if not (3<=seconds<=3600) or safe<3:raise ValueError('Not enough reliably measured time remains.')
    return {'estimated_seconds':seconds,'safe_seconds':safe,'fraction':float(f[-1]),
            'observed_seconds':float(duration),'observed_at':float(a[-1,0]),
            'deadline':float(a[-1,0]+safe),'source':'Gartic pie movement; approximate'}


def observe_timer(capture,canvas_box,stop,report=lambda text:None,clock=time.monotonic):
    observations=[];ring=None
    for index in range(7):
        if stop.is_set():raise InterruptedError()
        shot=capture()
        if ring is None:ring=find_timer(shot,canvas_box,stop.is_set)
        reading=read_ring(shot,ring['box'])
        observations.append((clock(),reading['fraction']))
        report(f'Reading Gartic timer {index+1}/7 · {reading["fraction"]*100:.0f}% visible')
        if index<6 and stop.wait(1):raise InterruptedError()
    result=estimate_remaining(observations);result['box']=ring['box']
    return result


def apply_timer_budget(options,reading,clock=time.monotonic):
    remaining=math.floor(float(reading['deadline'])-clock())
    if not 5<=remaining<=3600:raise ValueError('Too little reliably measured Gartic time remains to start.')
    out=dict(options,max_seconds=remaining,manual_max_seconds=remaining,time_budget_seconds=remaining,
             time_budget_mode='Manual',time_budget_active=False,
             gartic_timer_deadline=float(reading['deadline']),gartic_timer_meta=dict(reading))
    if out.get('outline'):out['sketch_detail']='Auto'
    return out
