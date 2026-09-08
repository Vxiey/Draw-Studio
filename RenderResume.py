"""Crash-safe deterministic render resume helpers for Draw Studio v1.0.79.

Schema 2 keeps the existing completed-color checkpoint and can additionally
identify the next *uncompleted path* inside the active browser color batch.
It never stores or restores input authorization.
"""
from __future__ import annotations

import hashlib
import json

SCHEMA = 2
SUPPORTED_SCHEMAS = (1, 2)


def _clean_rgb(value):
    try:
        return tuple(max(0, min(255, int(v))) for v in value[:3])
    except Exception:
        return (0, 0, 0)


def active_color_order(plan):
    groups = plan.get('groups') or []
    execution_groups = plan.get('execution_groups')
    requested = (plan.get('options') or {}).get('color_order') or list(range(len(groups)))
    result = []
    for raw in requested:
        try:index = int(raw)
        except (TypeError, ValueError):continue
        if not 0 <= index < len(groups):continue
        has_strokes = bool(groups[index])
        has_paths = bool(execution_groups is not None and index < len(execution_groups) and execution_groups[index])
        if has_strokes or has_paths:result.append(index)
    return result


def batch_key(plan, index):
    colors = plan.get('colors') or ()
    selectors = plan.get('color_selectors') or ()
    rgb = _clean_rgb(colors[index] if index < len(colors) else (0, 0, 0))
    selector = selectors[index] if index < len(selectors) and isinstance(selectors[index], dict) else {}
    payload = {
        'index': int(index), 'rgb': rgb, 'kind': str(selector.get('kind') or 'palette'),
        'palette_index': selector.get('palette_index'), 'fallback_palette_index': selector.get('fallback_palette_index'),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()[:20]


def items_fingerprint(items) -> str:
    """Fingerprint the actual ordered path list without storing source pixels."""
    h=hashlib.sha256()
    try:
        for item in items or ():
            if isinstance(item,(list,tuple)):
                h.update(repr(tuple(tuple(v) if isinstance(v,(list,tuple)) else v for v in item)).encode('utf-8'))
            else:h.update(repr(item).encode('utf-8'))
            h.update(b'|')
    except Exception:
        h.update(repr(items).encode('utf-8'))
    return h.hexdigest()


def plan_fingerprint(plan):
    h = hashlib.sha256()
    image = plan.get('image')
    if image is not None:
        try:
            rgb = image.convert('RGB');h.update(f'image:{rgb.width}x{rgb.height}:'.encode());h.update(rgb.tobytes())
        except Exception:h.update(repr(getattr(image, 'size', None)).encode())
    h.update(repr(tuple(plan.get('fitted') or ())).encode())
    h.update(repr(tuple(_clean_rgb(c) for c in (plan.get('colors') or ()))).encode())
    order = active_color_order(plan);h.update(repr(tuple(order)).encode());h.update(str(int(plan.get('count') or 0)).encode())
    selectors=[]
    for index in order:
        src=(plan.get('color_selectors') or ())
        selector=src[index] if index < len(src) and isinstance(src[index],dict) else {}
        selectors.append((selector.get('kind'),selector.get('palette_index'),selector.get('fallback_palette_index'),_clean_rgb(selector.get('rgb') or (0,0,0))))
    h.update(repr(tuple(selectors)).encode())
    return h.hexdigest()


def _base(plan, completed_count, *, prelude_complete=True):
    order=active_color_order(plan);completed=max(0,min(int(completed_count),len(order)))
    return {
        'schema':SCHEMA,'plan_fingerprint':plan_fingerprint(plan),'total_colors':len(order),
        'completed_count':completed,'completed_keys':[batch_key(plan,index) for index in order[:completed]],
        'next_color':completed+1 if completed < len(order) else 0,'prelude_complete':bool(prelude_complete),
        'active_color_number':0,'active_color_index':None,'active_batch_key':'','next_path_index':0,
        'active_path_count':0,'active_items_fingerprint':'','path_level':False,
    }


def new_progress(plan):
    return _base(plan,0,prelude_complete=False)


def checkpoint_after_batch(plan, completed_count, *, prelude_complete=True):
    return _base(plan,completed_count,prelude_complete=prelude_complete)


def checkpoint_before_path(plan, color_number, path_index, path_count, *, ordered_items=None, prelude_complete=True):
    order=active_color_order(plan);color_number=int(color_number)
    if not 1 <= color_number <= len(order):raise ValueError('Invalid active color number for path checkpoint.')
    path_count=max(0,int(path_count));path_index=max(0,min(int(path_index),path_count))
    color_index=order[color_number-1]
    out=_base(plan,color_number-1,prelude_complete=prelude_complete)
    out.update({
        'next_color':color_number,'active_color_number':color_number,'active_color_index':int(color_index),
        'active_batch_key':batch_key(plan,color_index),'next_path_index':path_index,
        'active_path_count':path_count,'active_items_fingerprint':items_fingerprint(ordered_items),
        'path_level':True,
    })
    return out


def checkpoint_after_path(plan, color_number, completed_path_index, path_count, *, ordered_items=None, prelude_complete=True):
    return checkpoint_before_path(plan,color_number,int(completed_path_index)+1,path_count,
                                  ordered_items=ordered_items,prelude_complete=prelude_complete)


def validate_progress(value):
    if not isinstance(value,dict):return None
    try:schema=int(value.get('schema',0))
    except (TypeError,ValueError):return None
    if schema not in SUPPORTED_SCHEMAS:return None
    fp=value.get('plan_fingerprint')
    try:
        total=max(0,int(value.get('total_colors',0)));completed=max(0,min(int(value.get('completed_count',0)),total))
    except (TypeError,ValueError):return None
    keys=value.get('completed_keys') or []
    if not isinstance(fp,str) or len(fp)!=64 or not isinstance(keys,list):return None
    keys=[str(k)[:40] for k in keys[:completed]]
    if len(keys)!=completed:return None
    out={
        'schema':schema,'plan_fingerprint':fp,'total_colors':total,'completed_count':completed,'completed_keys':keys,
        'next_color':completed+1 if completed<total else 0,'prelude_complete':bool(value.get('prelude_complete')),
        'active_color_number':0,'active_color_index':None,'active_batch_key':'','next_path_index':0,
        'active_path_count':0,'active_items_fingerprint':'','path_level':False,
    }
    if schema>=2 and bool(value.get('path_level')):
        try:
            n=max(0,int(value.get('active_color_number',0)));idx=int(value.get('active_color_index'))
            nxt=max(0,int(value.get('next_path_index',0)));count=max(0,int(value.get('active_path_count',0)))
        except (TypeError,ValueError):return None
        key=str(value.get('active_batch_key') or '')[:40];items_fp=str(value.get('active_items_fingerprint') or '')
        if n != completed+1 or not 1 <= n <= total or nxt>count or len(key)<8 or len(items_fp)!=64:return None
        out.update({'active_color_number':n,'active_color_index':idx,'active_batch_key':key,
                    'next_path_index':nxt,'active_path_count':count,'active_items_fingerprint':items_fp,
                    'next_color':n,'path_level':True})
    return out


def resolve_resume(plan,state):
    clean=validate_progress(state);order=active_color_order(plan)
    if not clean or (not clean['completed_count'] and not clean.get('path_level')):
        return {'compatible':False,'completed_count':0,'total_colors':len(order),'reason':'no completed color/path progress'}
    if plan.get('execution_sequence'):
        return {'compatible':False,'completed_count':0,'total_colors':len(order),'reason':'progressive passes cannot resume by deterministic color path'}
    if clean['plan_fingerprint'] != plan_fingerprint(plan):
        return {'compatible':False,'completed_count':0,'total_colors':len(order),'reason':'final plan fingerprint changed'}
    if clean['total_colors'] != len(order):
        return {'compatible':False,'completed_count':0,'total_colors':len(order),'reason':'color batch count changed'}
    expected=[batch_key(plan,index) for index in order[:clean['completed_count']]]
    if expected != clean['completed_keys']:
        return {'compatible':False,'completed_count':0,'total_colors':len(order),'reason':'completed color sequence changed'}
    result={
        'compatible':True,'completed_count':clean['completed_count'],'total_colors':len(order),
        'next_color':clean['next_color'],'prelude_complete':bool(clean['prelude_complete']),'reason':'',
        'path_level':False,'active_color_number':0,'active_color_index':None,'next_path_index':0,
        'active_path_count':0,'active_items_fingerprint':'',
    }
    if clean.get('path_level'):
        n=clean['active_color_number'];index=order[n-1]
        if index != clean['active_color_index'] or batch_key(plan,index)!=clean['active_batch_key']:
            return {'compatible':False,'completed_count':0,'total_colors':len(order),'reason':'active color batch changed'}
        result.update({'path_level':True,'active_color_number':n,'active_color_index':index,
                       'next_path_index':clean['next_path_index'],'active_path_count':clean['active_path_count'],
                       'active_items_fingerprint':clean['active_items_fingerprint']})
    return result
