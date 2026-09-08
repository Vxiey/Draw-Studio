"""Deterministic subject selection. No semantic person detection or ML."""
from collections import deque
from dataclasses import replace
import math
import numpy as np
from PIL import Image

MODES = ('Off', 'Subject first', 'Subject only')

def rectangle_mask(size, region):
    width, height = size
    if len(region) != 4 or not all(math.isfinite(float(v)) for v in region):
        raise ValueError('Invalid subject rectangle. Mark the subject again.')
    x0, y0, x1, y1 = map(float, region)
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise ValueError('Subject rectangle must be inside the image.')
    mask = np.zeros((height, width), dtype=bool)
    mask[int(y0*height):math.ceil(y1*height), int(x0*width):math.ceil(x1*width)] = True
    return mask

def subject_mask(image, region=None, cancelled=lambda: False):
    """Use explicit rectangle, alpha, or border-connected uniform background.

    Automatic mode deliberately refuses complex borders. It is an estimate,
    never a claim that a person was recognized. Mask estimation is bounded;
    the original image and full-resolution PixelMap are not resampled here.
    """
    if cancelled(): raise InterruptedError()
    if region is not None:
        return rectangle_mask(image.size, region), 'Marked rectangle (includes its background)'
    alpha = np.asarray(image.convert('RGBA').getchannel('A'))
    if np.any(alpha == 0) and np.any(alpha > 0):
        return alpha > 0, 'Image transparency'
    small = image.convert('RGB')
    small.thumbnail((384, 384))
    rgb = np.asarray(small, dtype=np.int16)
    border = np.concatenate((rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]))
    bg = np.median(border, axis=0)
    distances = np.max(np.abs(border-bg), axis=1)
    if np.mean(distances <= 28) < .85:
        raise ValueError('Background is too complex for automatic subject selection. Click Mark subject and draw a rectangle, or use a transparent PNG.')
    candidate = np.max(np.abs(rgb-bg), axis=2) <= 28
    h, w = candidate.shape
    visited = np.zeros_like(candidate)
    queue = deque()
    def add(y, x):
        if candidate[y, x] and not visited[y, x]:
            visited[y, x] = True
            queue.append((y, x))
    for x in range(w): add(0, x); add(h-1, x)
    for y in range(h): add(y, 0); add(y, w-1)
    count = 0
    while queue:
        y, x = queue.popleft()
        count += 1
        if count % 1024 == 0 and cancelled(): raise InterruptedError()
        if y: add(y-1, x)
        if y+1 < h: add(y+1, x)
        if x: add(y, x-1)
        if x+1 < w: add(y, x+1)
    mask = np.asarray(Image.fromarray((~visited).astype('uint8')*255).resize(image.size, Image.Resampling.NEAREST)) > 0
    if not mask.any() or mask.mean() > .95:
        raise ValueError('No clear subject found. Click Mark subject or use a transparent PNG.')
    return mask, 'Estimated from uniform border; check Coverage preview'

def focused_stroke_plan(pixel_map, image, palette_count, mode, region=None, *, lines=True, cpu_workers=1, cancelled=lambda: False):
    from PixelStrokeEngine import build_pixel_stroke_plan
    from PixelAccuracyEngine import execution_groups_from_sequence
    if mode not in MODES: raise ValueError('Unknown subject focus mode')
    kwargs = dict(lines=lines, cpu_workers=cpu_workers, cancelled=cancelled)
    if mode == 'Off':
        return pixel_map, build_pixel_stroke_plan(pixel_map, palette_count, **kwargs)
    mask, method = subject_mask(image, region, cancelled)
    foreground = pixel_map.drawable_mask & mask
    if not foreground.any():
        raise ValueError('The selected subject has no drawable pixels. Check the selection, palette and Skip white.')
    meta = dict(pixel_map.metadata, subject_focus=mode, subject_method=method,
                subject_pixels=int(foreground.sum()), subject_share=round(float(foreground.sum())/max(1,int(pixel_map.drawable_mask.sum())),4))
    def subset(selection):
        return replace(pixel_map, drawable_mask=selection,
                       protected_mask=pixel_map.protected_mask & selection, metadata=meta)
    target = subset(foreground) if mode == 'Subject only' else replace(pixel_map, metadata=meta)
    plans = [('subject', build_pixel_stroke_plan(subset(foreground), palette_count, **kwargs))]
    if mode == 'Subject first':
        plans.append(('background', build_pixel_stroke_plan(subset(pixel_map.drawable_mask & ~mask), palette_count, **kwargs)))
    groups = [[] for _ in range(palette_count)]
    sequence = []
    for section, plan in plans:
        for ci, group in enumerate(plan['groups']): groups[ci].extend(group)
        for entry in plan['execution_sequence']:
            # The timer preserves these section-prefixed phases as ordered paths.
            sequence.append(dict(entry, phase=section+'/'+entry['phase'],
                                 phase_label=section+' / '+entry.get('phase_label',entry['phase']),
                                 serial=len(sequence), subject_section=section))
    return target, dict(groups=groups, execution_groups=execution_groups_from_sequence(sequence,palette_count),
                       execution_sequence=sequence, metadata=dict(engine='Subject Focus / Pixel Stroke Engine',
                       execution_paths=len(sequence), subject_focus=mode, subject_method=method,
                       sections={section:plan['metadata'] for section,plan in plans}))
