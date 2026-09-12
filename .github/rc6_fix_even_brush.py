from pathlib import Path

p=Path('AdaptiveRegionHybrid.py')
text=p.read_text(encoding='utf-8')
old='''def _eroded_centers(target:np.ndarray,brush_px:int) -> np.ndarray:
    b=max(1,int(brush_px));lo=(b-1)//2;hi=b//2
    valid=np.ones_like(target)
    h,w=target.shape
    for dy in range(-lo,hi+1):
        for dx in range(-lo,hi+1):
            shifted=np.zeros_like(target)
            ys=slice(max(0,-dy),min(h,h-dy));yd=slice(max(0,dy),min(h,h+dy))
            xs=slice(max(0,-dx),min(w,w-dx));xd=slice(max(0,dx),min(w,w+dx))
            shifted[yd,xd]=target[ys,xs]
            valid &= shifted
    return valid
'''
new='''def _eroded_centers(target:np.ndarray,brush_px:int) -> np.ndarray:
    """Centres whose simulated brush footprint stays entirely in target.

    For even brushes _paint_path uses an asymmetric footprint (for 2 px: the
    centre pixel plus +1).  The erosion must use that same direction or the
    planner approves the wrong border and leaves the opposite border uncovered.
    """
    b=max(1,int(brush_px));lo=(b-1)//2;hi=b//2
    valid=np.ones_like(target,dtype=np.bool_);h,w=target.shape
    for dy in range(-lo,hi+1):
        for dx in range(-lo,hi+1):
            shifted=np.zeros_like(target,dtype=np.bool_)
            yd=slice(max(0,-dy),min(h,h-dy));ys=slice(max(0,dy),min(h,h+dy))
            xd=slice(max(0,-dx),min(w,w-dx));xs=slice(max(0,dx),min(w,w+dx))
            shifted[yd,xd]=target[ys,xs]
            valid &= shifted
    return valid
'''
if old not in text:raise SystemExit('rc6 even-brush erosion anchor missing')
text=text.replace(old,new,1)
old='''def _centers_touching_mask(mask:np.ndarray,brush_px:int) -> np.ndarray:
    """Return centres whose brush footprint touches at least one wanted pixel."""
    b=max(1,int(brush_px));lo=(b-1)//2;hi=b//2
    touch=np.zeros_like(mask,dtype=np.bool_);h,w=mask.shape
    for dy in range(-lo,hi+1):
        for dx in range(-lo,hi+1):
            shifted=np.zeros_like(mask,dtype=np.bool_)
            ys=slice(max(0,-dy),min(h,h-dy));yd=slice(max(0,dy),min(h,h+dy))
            xs=slice(max(0,-dx),min(w,w-dx));xd=slice(max(0,dx),min(w,w+dx))
            shifted[yd,xd]=mask[ys,xs]
            touch |= shifted
    return touch
'''
new='''def _centers_touching_mask(mask:np.ndarray,brush_px:int) -> np.ndarray:
    """Return centres whose simulated footprint touches at least one wanted pixel."""
    b=max(1,int(brush_px));lo=(b-1)//2;hi=b//2
    touch=np.zeros_like(mask,dtype=np.bool_);h,w=mask.shape
    for dy in range(-lo,hi+1):
        for dx in range(-lo,hi+1):
            shifted=np.zeros_like(mask,dtype=np.bool_)
            yd=slice(max(0,-dy),min(h,h-dy));ys=slice(max(0,dy),min(h,h+dy))
            xd=slice(max(0,-dx),min(w,w-dx));xs=slice(max(0,dx),min(w,w+dx))
            shifted[yd,xd]=mask[ys,xs]
            touch |= shifted
    return touch
'''
if old not in text:raise SystemExit('rc6 touching-mask anchor missing')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('rc6 even-brush geometry fixed')
