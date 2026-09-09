"""Read-only modern Paint setup, verified against ribbon geometry and icons."""
import numpy as np
from PIL import Image,ImageFilter
from PaletteMaps import detect_color_swatches
from RuntimePaths import resource_path

ROW1=((0,0,0),(127,127,127),(136,0,21),(237,28,36),(255,127,39),(255,242,0),(34,177,76),(0,162,232),(63,72,204),(163,73,164))
ROW2=((255,255,255),(195,195,195),(185,122,87),(255,174,201),(255,201,14),(239,228,176),(181,230,29),(153,217,234),(112,146,190),(200,191,231))


def _run(mask):
    best=(0,0);start=None
    for i,value in enumerate(list(mask)+[False]):
        if value and start is None:start=i
        elif not value and start is not None:
            if i-start>best[1]-best[0]:best=(start,i)
            start=None
    return best


def _detect_visible_canvas(white, *, toolbar_end, w, h, scale, screen_origin, ratio):
    """Return a safe visible Paint drawing area, even when the document is clipped.

    Modern Paint commonly lets the document extend beyond the client viewport.  A
    clipped document edge is not itself unsafe: Draw Studio only needs a verified
    blank visible drawing rectangle.  Edges that are visible still have to be
    bounded by non-canvas pixels, while edges that coincide with the client
    boundary are inset more aggressively before being returned.
    """
    top,bottom=_run(np.mean(white,axis=1)>.35)
    if bottom-top<h*.25:
        raise ValueError('No blank Paint canvas found. Open a blank canvas or select the drawing area manually.')
    left,right=_run(np.mean(white[top:bottom],axis=0)>.995)
    if right-left<w*.35:
        raise ValueError('Paint canvas visible area is too small. Enlarge Paint or select the drawing area manually.')
    if np.mean(white[top:bottom,left:right])<.999:
        raise ValueError('Paint canvas is not blank or is covered. Clear it or select the area manually.')

    clipped=[]
    if left<2:clipped.append('left')
    if right>w-2:clipped.append('right')
    if bottom>h-2:clipped.append('bottom')

    # A real visible Paint border is surrounded by non-white workspace pixels.
    # Do not index outside the screenshot for document edges clipped by the
    # client viewport; those are valid and are handled by the larger inset below.
    edges=[]
    if left>0:edges.append(white[top:bottom,left-1])
    if right<w:edges.append(white[top:bottom,right])
    if top>0:edges.append(white[top-1,left:right])
    if bottom<h:edges.append(white[bottom,left:right])
    if any(float(np.mean(edge))>.10 for edge in edges):
        raise ValueError('Paint canvas border is ambiguous or covered. Clear Paint or select the drawing area manually.')

    normal_inset=max(2,round(2*scale))
    clipped_inset=max(normal_inset+2,round(6*scale))
    x0=left+(clipped_inset if 'left' in clipped else normal_inset)
    x1=right-(clipped_inset if 'right' in clipped else normal_inset)
    y0=top+normal_inset
    y1=bottom-(clipped_inset if 'bottom' in clipped else normal_inset)
    if x1-x0<max(24,round(80*scale)) or y1-y0<max(24,round(80*scale)):
        raise ValueError('Paint canvas safe visible area is too small. Enlarge Paint or select the drawing area manually.')

    box=(round(x0/ratio)+screen_origin[0],round(y0/ratio)+screen_origin[1],
         round(x1/ratio)+screen_origin[0],round(y1/ratio)+screen_origin[1])
    return box,tuple(clipped)


def detect_setup(image,screen_origin=(0,0),cancelled=lambda:False):
    if cancelled():raise InterruptedError()
    # Bound detection arrays and component scans independently of screen DPI.
    ratio=min(1.,1920/image.width,1200/image.height)
    work=image.resize((round(image.width*ratio),round(image.height*ratio))).convert('RGB')
    w,h=work.size;rh=min(h//2,360)
    pos,colors,_=detect_color_swatches(work.crop((0,0,w,rh)))
    if cancelled():raise InterruptedError()
    # Nine ordered colour anchors rule out arbitrary dense toolbar icons.
    matches=[]
    for expected in ROW1[1:]:
        hits=[p for p,c in zip(pos,colors) if max(abs(a-b) for a,b in zip(c,expected))<=8]
        if len(hits)!=1:raise ValueError('Paint colour ribbon was not recognized. Expand the ribbon and use the light theme, or calibrate manually.')
        matches.append(hits[0])
    pitch,anchor_x=map(float,np.polyfit(np.arange(1,10),[p[0] for p in matches],1))
    scale=pitch/24.;anchor_y=float(np.median([p[1] for p in matches]))
    if not .55<=scale<=2 or any(abs(p[0]-(anchor_x+(i+1)*pitch))>2.5*scale or abs(p[1]-anchor_y)>2.5*scale for i,p in enumerate(matches)):
        raise ValueError('Paint palette grid is ambiguous. Keep the complete ribbon visible.')
    positions=[];rgbs=[]
    for row,expected_row in enumerate((ROW1,ROW2)):
        for col,expected in enumerate(expected_row):
            x,y=round(anchor_x+col*pitch),round(anchor_y+row*pitch)
            if not (2<=x<w-2 and 2<=y<rh-2):raise ValueError('Paint palette is clipped.')
            pixels=np.asarray(work.crop((x-1,y-1,x+2,y+2)),dtype=np.int16)
            rgb=tuple(int(v) for v in np.median(pixels.reshape(-1,3),axis=0))
            if max(abs(a-b) for a,b in zip(rgb,expected))>10 or np.max(np.ptp(pixels.reshape(-1,3),axis=0))>10:
                raise ValueError('Paint colour cells are covered or changed. Close menus and try again.')
            positions.append((round(x/ratio)+screen_origin[0],round(y/ratio)+screen_origin[1]));rgbs.append(rgb)
    reference=Image.open(resource_path('assets/paint-tools-reference.png')).convert('RGB')
    tools={}
    for name,rx,ry in (('Pencil',268,88),('Fill',308,88),('Eraser',268,128)):
        cx=anchor_x+(rx-794)*scale;cy=anchor_y+(ry-83)*scale
        radius=12*scale
        if cx-radius<0 or cy-radius<0:raise ValueError('Paint tools are clipped.')
        expected=reference.crop((rx-250-12,ry-70-12,rx-250+12,ry-70+12))
        best=(float('inf'),cx,cy)
        for dx in (-2,0,2):
            for dy in (-2,0,2):
                x,y=cx+dx*scale,cy+dy*scale
                actual=work.crop((round(x-radius),round(y-radius),round(x+radius),round(y+radius))).resize((24,24))
                aa=np.asarray(actual);ee=np.asarray(expected)
                am=np.min(aa,axis=2)<170;em=np.min(ee,axis=2)<170
                ad=np.asarray(Image.fromarray(am.astype('uint8')*255).filter(ImageFilter.MaxFilter(3)))>0
                ed=np.asarray(Image.fromarray(em.astype('uint8')*255).filter(ImageFilter.MaxFilter(3)))>0
                overlap=min(float(np.sum(am&ed))/max(1,int(am.sum())),float(np.sum(em&ad))/max(1,int(em.sum())))
                difference=float(np.mean(np.abs(aa.astype(float)-ee.astype(float)))) if overlap>=.75 else float('inf')
                if difference<best[0]:best=(difference,x,y)
        difference,cx,cy=best
        if difference>32:raise ValueError(f'Paint {name} icon could not be verified. Close menus or use manual tool calibration.')
        tools[name]=(round(cx/ratio)+screen_origin[0],round(cy/ratio)+screen_origin[1])
    if cancelled():raise InterruptedError()
    a=np.asarray(work);white=np.min(a,axis=2)>=253
    toolbar_end=min(h,round(anchor_y+100*scale));white[:toolbar_end]=False
    box,clipped_edges=_detect_visible_canvas(white,toolbar_end=toolbar_end,w=w,h=h,scale=scale,
                                              screen_origin=screen_origin,ratio=ratio)
    clipped=bool(clipped_edges)
    return {'tools':tools,'positions':positions,'rgbs':rgbs,'canvas_box':box,'palette_count':len(rgbs),
            'confidence':.87 if clipped else .90,
            'method':'modern-paint-grid-and-icons-v3',
            'canvas_visibility':'viewport-clipped' if clipped else 'full',
            'canvas_clipped_edges':list(clipped_edges)}


def save_setup(result,meta,palette_path,tool_path=None):
    from Colors import save_calibration
    from PaintTools import save_tool_calibration,TOOL_FILE
    from CalibrationAnchors import make_anchor
    anchor=make_anchor(meta['client_rect'])
    # Detection is complete before either persisted calibration is changed.
    save_tool_calibration(result['tools'],path=tool_path or TOOL_FILE,anchor=anchor,
                          auto={'method':result['method'],'confidence':result['confidence'],'detected':list(result['tools'])})
    save_calibration(result['positions'],result['rgbs'],palette_path,anchor=anchor,profile_key='microsoft-paint',state='verified',verification={'method':str(result.get('method') or 'paint-auto-calibration'),'confidence':float(result.get('confidence',0) or 0),'source':'paint-screen-verification'})
    return dict(result,target_meta=meta)


def choose_paint_window(windows):
    import re
    matches=[m for m in windows if re.search(r'(?:^|[–—-]\s*)Paint\s*$',str(m.get('title','')),re.I)]
    if len(matches)!=1:raise ValueError('Keep exactly one Paint window open and visible, then try Auto setup again.')
    return matches[0]
