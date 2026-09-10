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


def _significant_runs(mask,min_length):
    out=[];start=None
    for i,value in enumerate(list(mask)+[False]):
        if value and start is None:start=i
        elif not value and start is not None:
            if i-start>=min_length:out.append((start,i))
            start=None
    return out


def _edge_supported_horizontal_span(white, *, top, bottom, scale, min_safe_w):
    """Infer the document span from clean bands near its top/bottom edges.

    Interior ink/overlays must not make calibration silently shrink to a smaller
    white sub-rectangle.  Paint's top and bottom document bands normally retain
    the true horizontal extent, while using the maximum of both bands tolerates
    a resize handle or shadow affecting only one edge.  Significant separated
    white runs are enveloped so an interior obstruction is caught later by the
    blankness check instead of becoming a fake new canvas edge.
    """
    probe_h=max(3,round(6*scale));inset=max(3,round(10*scale))
    profiles=[]
    for y0 in (top+inset,bottom-inset-probe_h):
        y0=int(y0)
        if y0>=top and y0+probe_h<=bottom:
            profiles.append(np.mean(white[y0:y0+probe_h],axis=0))
    if not profiles:return (0,0)
    support=np.maximum.reduce(profiles)
    runs=_significant_runs(support>.985,max(8,round(20*scale)))
    if not runs:return (0,0)
    left,right=runs[0][0],runs[-1][1]
    return (left,right) if right-left>=min_safe_w else (0,0)


def _border_band_has_workspace(white, side, *, left, right, top, bottom, width, trim, toolbar_end):
    """Verify a visible canvas edge using an outside band, not one brittle pixel line.

    Current Paint can draw a light canvas shadow, anti-aliased border or resize
    handle immediately outside the document.  A single outside row/column can
    therefore contain enough pure-white pixels to look like more canvas even
    though grey workspace is present a few pixels farther out.  We accept the
    edge when the outside band contains substantial workspace overall or a
    continuous non-white separator along most of the edge.
    """
    h,w=white.shape
    trim=max(0,int(trim));width=max(1,int(width))
    y0=min(bottom,top+trim);y1=max(y0+1,bottom-trim)
    x0=min(right,left+trim);x1=max(x0+1,right-trim)
    if side=='left':
        if left<=0:return True
        band=white[y0:y1,max(0,left-width):left]
        line_axis=1
    elif side=='right':
        if right>=w:return True
        band=white[y0:y1,right:min(w,right+width)]
        line_axis=1
    elif side=='top':
        if top<=toolbar_end:return True
        band=white[max(toolbar_end,top-width):top,x0:x1]
        line_axis=0
    elif side=='bottom':
        if bottom>=h:return True
        band=white[bottom:min(h,bottom+width),x0:x1]
        line_axis=0
    else:
        raise ValueError(f'Unknown Paint canvas edge: {side}')
    if band.size==0:return False
    nonwhite=np.logical_not(band)
    density=float(np.mean(nonwhite))
    line_density=np.mean(nonwhite,axis=line_axis)
    thickness=band.shape[1] if line_axis==1 else band.shape[0]
    separator_threshold=max(.04,min(.20,.75/max(1,thickness)))
    separator_support=float(np.mean(line_density>=separator_threshold)) if line_density.size else 0.
    return density>=.14 or separator_support>=.80


def _detect_visible_canvas(white, *, toolbar_end, w, h, scale, screen_origin, ratio):
    """Return a safe visible Paint drawing area, including compact/clipped viewports."""
    min_safe_w=max(96,round(160*scale))
    min_safe_h=max(96,round(120*scale))

    row_fraction=min(.35,max(.06,(min_safe_w/max(1,w))*.72))
    top,bottom=_run(np.mean(white,axis=1)>row_fraction)
    if bottom-top<min_safe_h:
        raise ValueError('Paint canvas visible area is too small. Enlarge Paint or select the drawing area manually.')

    # Prefer the document envelope inferred from near-edge bands.  This keeps a
    # central obstruction inside the candidate so blankness verification rejects
    # it rather than silently selecting one white side of the document.
    left,right=_edge_supported_horizontal_span(white,top=top,bottom=bottom,scale=scale,min_safe_w=min_safe_w)
    if right-left<min_safe_w:
        edge_trim=max(2,round(8*scale))
        sample_top=min(bottom,top+edge_trim)
        sample_bottom=max(sample_top+1,bottom-edge_trim)
        column_white=np.mean(white[sample_top:sample_bottom],axis=0)
        left,right=_run(column_white>.985)
    if right-left<min_safe_w:
        raise ValueError('Paint canvas visible area is too small. Enlarge Paint or select the drawing area manually.')

    verify_inset=max(2,round(5*scale))
    vy0=min(bottom,top+verify_inset);vy1=max(vy0+1,bottom-verify_inset)
    vx0=min(right,left+verify_inset);vx1=max(vx0+1,right-verify_inset)
    interior=white[vy0:vy1,vx0:vx1]
    if interior.size==0 or float(np.mean(interior))<.997:
        raise ValueError('Paint canvas is not blank or is covered. Clear it or select the area manually.')

    edge_tol=max(2,round(3*scale))
    clipped=[]
    if left<=edge_tol:clipped.append('left')
    if right>=w-edge_tol:clipped.append('right')
    if bottom>=h-edge_tol:clipped.append('bottom')

    band_width=max(3,round(6*scale));border_trim=max(4,round(12*scale))
    visible_sides=[]
    if left>edge_tol:visible_sides.append('left')
    if right<w-edge_tol:visible_sides.append('right')
    if top>toolbar_end:visible_sides.append('top')
    if bottom<h-edge_tol:visible_sides.append('bottom')
    if any(not _border_band_has_workspace(white,side,left=left,right=right,top=top,bottom=bottom,
                                           width=band_width,trim=border_trim,toolbar_end=toolbar_end)
           for side in visible_sides):
        raise ValueError('Paint canvas border is ambiguous or covered. Clear Paint or select the drawing area manually.')

    normal_inset=max(2,round(2*scale))
    clipped_inset=max(normal_inset+2,round(6*scale))
    x0=left+(clipped_inset if 'left' in clipped else normal_inset)
    x1=right-(clipped_inset if 'right' in clipped else normal_inset)
    y0=top+normal_inset
    y1=bottom-(clipped_inset if 'bottom' in clipped else normal_inset)
    if x1-x0<max(64,round(120*scale)) or y1-y0<max(64,round(90*scale)):
        raise ValueError('Paint canvas safe visible area is too small. Enlarge Paint or select the drawing area manually.')

    box=(round(x0/ratio)+screen_origin[0],round(y0/ratio)+screen_origin[1],
         round(x1/ratio)+screen_origin[0],round(y1/ratio)+screen_origin[1])
    compact=(right-left)<w*.35 or (bottom-top)<max(1,h-toolbar_end)*.35
    return box,tuple(clipped),compact


def detect_setup(image,screen_origin=(0,0),cancelled=lambda:False):
    if cancelled():raise InterruptedError()
    ratio=min(1.,1920/image.width,1200/image.height)
    work=image.resize((round(image.width*ratio),round(image.height*ratio))).convert('RGB')
    w,h=work.size;rh=min(h//2,360)
    pos,colors,_=detect_color_swatches(work.crop((0,0,w,rh)))
    if cancelled():raise InterruptedError()
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
    box,clipped_edges,compact=_detect_visible_canvas(white,toolbar_end=toolbar_end,w=w,h=h,scale=scale,
                                                      screen_origin=screen_origin,ratio=ratio)
    clipped=bool(clipped_edges)
    return {'tools':tools,'positions':positions,'rgbs':rgbs,'canvas_box':box,'palette_count':len(rgbs),
            'confidence':.85 if compact else (.87 if clipped else .90),
            'method':'modern-paint-grid-and-icons-v6',
            'canvas_visibility':'viewport-compact' if compact else ('viewport-clipped' if clipped else 'full'),
            'canvas_clipped_edges':list(clipped_edges)}


def save_setup(result,meta,palette_path,tool_path=None):
    from Colors import save_calibration
    from PaintTools import save_tool_calibration,TOOL_FILE
    from CalibrationAnchors import make_anchor
    anchor=make_anchor(meta['client_rect'])
    save_tool_calibration(result['tools'],path=tool_path or TOOL_FILE,anchor=anchor,
                          auto={'method':result['method'],'confidence':result['confidence'],'detected':list(result['tools'])})
    save_calibration(result['positions'],result['rgbs'],palette_path,anchor=anchor,profile_key='microsoft-paint',state='verified',verification={'method':str(result.get('method') or 'paint-auto-calibration'),'confidence':float(result.get('confidence',0) or 0),'source':'paint-screen-verification'})
    return dict(result,target_meta=meta)


def choose_paint_window(windows):
    import re
    matches=[m for m in windows if re.search(r'(?:^|[–—-]\s*)Paint\s*$',str(m.get('title','')),re.I)]
    if len(matches)!=1:raise ValueError('Keep exactly one Paint window open and visible, then try Auto setup again.')
    return matches[0]
