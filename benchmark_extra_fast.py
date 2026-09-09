"""Synthetic source-raster benchmark; never sends mouse or network input."""
import json
from time import perf_counter
from PIL import Image, ImageDraw
from ContinuousPaths import build_execution_paths
from ExtraFast2 import build_fast_paths, path_limits


def raster(paths):
    im=Image.new('1',(320,320));draw=ImageDraw.Draw(im)
    for path in paths:
        if len(path)==1:draw.point(path[0],fill=1)
        else:draw.line(path,fill=1,width=1)
    return im.tobytes()


def run():
    cases={
        'vertical_block':[[(x,10,x,290) for x in range(10,290)]],
        'horizontal_block':[[(10,y,290,y) for y in range(10,290)]],
        'vertical_hole':[[(x,a,x,b) for x in range(10,290) for a,b in ([(10,100),(200,290)] if 100<=x<=200 else [(10,290)])]],
        'separate_colors':[[(x,10,x,290) for x in range(10,140)],[(x,10,x,290) for x in range(150,290)]],
        'thin_separated_lines':[[(x,10,x,290) for x in range(10,290,3)]],
        'mixed_axes':[[(x,10,x,140) for x in range(10,140)]+[(160,y,290,y) for y in range(160,290)]],
    }
    options={};rows,points,_=path_limits(options);results=[]
    for name,groups in cases.items():
        t=perf_counter()
        old=build_execution_paths(groups,enabled=True,max_rows_per_path=rows,max_points_per_path=points)
        old_ms=(perf_counter()-t)*1000
        t=perf_counter();new,meta=build_fast_paths(groups,options);new_ms=(perf_counter()-t)*1000
        exact=all(raster(o)==raster(n)==raster([[(a,b),(c,d)] for a,b,c,d in g]) for g,o,n in zip(groups,old,new))
        if not exact:raise AssertionError(name)
        results.append(dict(case=name,old_paths=sum(map(len,old)),new_paths=sum(map(len,new)),
                            exact_source_raster=exact,old_planning_ms=round(old_ms,3),new_planning_ms=round(new_ms,3),
                            intrinsic_before_seconds=meta['intrinsic_cost_before_seconds'],intrinsic_after_seconds=meta['intrinsic_cost_after_seconds']))
    return {'scope':'Synthetic source raster, width 1; estimated cost excludes travel and is not measured browser drawing speed. CPU timings are single runs.', 'cases':results}

if __name__=='__main__':print(json.dumps(run(),indent=2))
