"""Measure completed palette work including uploads/downloads, no mouse input.

Example: python benchmark_gpu_pipeline.py --mode "NVIDIA CUDA" --width 1024 --height 768
Uses the existing verified hardware profile. The reported backend is authoritative;
a requested GPU may fall back to CPU. First-call compilation is reported separately.
"""
import argparse
import json
import statistics
import time

import numpy as np
from PIL import Image

from UniversalGpuAcceleration import palette_indices_rgba


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('Auto','CPU','NVIDIA CUDA'),default='Auto')
    parser.add_argument('--width',type=int,default=512)
    parser.add_argument('--height',type=int,default=384)
    parser.add_argument('--colors',type=int,default=64)
    parser.add_argument('--repeats',type=int,default=3)
    args=parser.parse_args()
    if not (1<=args.width<=4096 and 1<=args.height<=4096 and 1<=args.colors<=256 and 1<=args.repeats<=20):
        parser.error('dimensions must be 1..4096, colors 1..256, repeats 1..20')
    rng=np.random.default_rng(830)
    image=Image.fromarray(rng.integers(0,256,(args.height,args.width,4),dtype=np.uint8))
    palette=rng.integers(0,256,(args.colors,3)).tolist()
    def run(mode):
        start=time.perf_counter()
        result,route=palette_indices_rgba(image,palette,range(args.colors),[False]*args.colors,gpu_mode=mode)
        return result,route,time.perf_counter()-start
    reference,_,cpu_seconds=run('CPU')
    actual,route,cold=run(args.mode)
    timings=[]
    for _ in range(args.repeats):
        actual,route,seconds=run(args.mode);timings.append(seconds)
    print(json.dumps(dict(requested_mode=args.mode,route=route,width=args.width,height=args.height,
                         colors=args.colors,first_call_seconds=cold,warm_median_seconds=statistics.median(timings),
                         warm_samples_seconds=timings,cpu_reference_seconds=cpu_seconds,
                         palette_index_mismatches=int(np.count_nonzero(reference[0]!=actual[0])),
                         visibility_mismatches=int(np.count_nonzero(reference[1]!=actual[1])),
                         timing_scope='completed palette mapping including host work, transfers and synchronization'),indent=2))


if __name__=='__main__':main()
