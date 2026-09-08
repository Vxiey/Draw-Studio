"""Trace connected black contours instead of painting one horizontal row at a time.

No gap bridging, arbitrary shortcuts or discarded components. Collinear points
are removed exactly. Long paths are split with shared endpoints for bounded work.
"""
import math
import numpy as np

def trace_contours(image, cancelled=lambda:False, max_points=160):
    if max_points<3:raise ValueError('max_points must be at least 3')
    if cancelled():raise InterruptedError()
    mask=np.asarray(image.convert('L'))<128
    nodes={(int(x),int(y)) for y,x in np.argwhere(mask)}
    graph={}
    for i,p in enumerate(sorted(nodes,key=lambda p:(p[1],p[0]))):
        if i%512==0 and cancelled():raise InterruptedError()
        x,y=p;neighbors=[]
        for dx,dy in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)):
            q=(x+dx,y+dy)
            if q not in nodes:continue
            # Avoid triangles across an already connected right-angle corner.
            if dx and dy and ((x+dx,y) in nodes or (x,y+dy) in nodes):continue
            neighbors.append(q)
        graph[p]=neighbors
    visited=set();paths=[]
    def edge(a,b):return (a,b) if a<b else (b,a)
    def walk(start,next_point):
        path=[start];previous=start;current=next_point
        visited.add(edge(previous,current))
        while True:
            path.append(current)
            if len(path)%256==0 and cancelled():raise InterruptedError()
            if len(graph[current])!=2:break
            choices=[q for q in graph[current] if edge(current,q) not in visited]
            if not choices:break
            nxt=choices[0];visited.add(edge(current,nxt));previous,current=current,nxt
        return path
    # Start at endpoints/junctions, then consume closed cycles.
    for p in graph:
        if cancelled():raise InterruptedError()
        if not graph[p]:paths.append([p])
        elif len(graph[p])!=2:
            for q in graph[p]:
                if edge(p,q) not in visited:paths.append(walk(p,q))
    for p in graph:
        if cancelled():raise InterruptedError()
        for q in graph[p]:
            if edge(p,q) not in visited:paths.append(walk(p,q))
    compressed=[]
    for path in paths:
        points=[]
        for pt in path:
            points.append(pt)
            while len(points)>=3:
                a,b,c=points[-3:];u=(b[0]-a[0],b[1]-a[1]);v=(c[0]-b[0],c[1]-b[1])
                if u[0]*v[1]!=u[1]*v[0] or u[0]*v[0]+u[1]*v[1]<=0:break
                points.pop(-2)
        compressed.append(tuple(points))
    def length(path):return sum(math.dist(a,b) for a,b in zip(path,path[1:]))
    compressed.sort(key=lambda path:-length(path)) # major contours before short details
    result=[]
    for path in compressed:
        if len(path)<=max_points:result.append(path)
        else:
            for i in range(0,len(path)-1,max_points-1):result.append(path[i:i+max_points])
    return result,{'engine':'Gartic connected contours','ink_pixels':len(nodes),
        'contours':len(paths),'execution_paths':len(result),
        'path_points':sum(map(len,result)),'priority':'long contours first',
        'gap_bridges':0,'dropped_components':0}
