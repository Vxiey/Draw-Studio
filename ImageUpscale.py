"""Bounded non-AI resampling; does not invent missing image detail."""
from PIL import Image, ImageOps
MAX_PIXELS = 25_000_000

def upscale_size(size, factor):
    if factor not in (2,4): raise ValueError('Choose 2× or 4×.')
    width,height=map(int,size)
    if min(width,height)<1: raise ValueError('Invalid image dimensions.')
    target=(width*factor,height*factor)
    if target[0]*target[1]>MAX_PIXELS:
        raise ValueError('Upscaled image would exceed 25 megapixels. Choose a smaller factor.')
    return target

def suggested_factor(size):
    longest=max(size)
    factor=4 if longest<512 else 2 if longest<1024 else 1
    while factor>1:
        try: upscale_size(size,factor); return factor
        except ValueError: factor//=2
    return 1

def upscale_image(image,factor=2,method='Smooth',cancelled=lambda:False):
    target=upscale_size(image.size,factor)
    if method not in ('Smooth','Pixel art'): raise ValueError('Unknown upscale method.')
    if cancelled(): raise InterruptedError()
    source=ImageOps.exif_transpose(image).convert('RGBA')
    # Recompute after EXIF rotation; preserve orientation and alpha correctly.
    target=upscale_size(source.size,factor)
    if method=='Pixel art':
        result=source.resize(target,Image.Resampling.NEAREST)
    else:
        # Premultiply alpha so hidden RGB cannot create dark/coloured fringes.
        result=source.convert('RGBa').resize(target,Image.Resampling.LANCZOS).convert('RGBA')
    if cancelled(): raise InterruptedError()
    result.info.update(source.info)
    result.info['draw_studio_upscale']=dict(factor=factor,method=method,source_size=source.size)
    return result
