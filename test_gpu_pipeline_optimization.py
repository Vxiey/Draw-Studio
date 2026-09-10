import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw

import UniversalGpuAcceleration as uga
from CudaPalette import OPERATION, PREAMBLE, match
from ExtraFast2 import build_fast_paths, _vertical_alternative


class PaletteOptimizationTests(unittest.TestCase):
    def test_chunked_palette_matches_dense_reference_and_first_ties(self):
        rng = np.random.default_rng(830)
        raw = rng.integers(0, 256, (3, 1401, 4), dtype=np.uint8)
        palette = rng.integers(0, 256, (71, 3)).tolist()
        palette[35] = palette[0]
        ids = np.array(list(reversed(range(71))), dtype=np.int16)
        custom = np.array([i % 5 == 0 for i in range(71)])
        alpha = raw[...,3:4].astype(np.float32)
        rgb = (raw[...,:3].astype(np.float32)*alpha+255*(255-alpha))/255
        for perceptual in (False, True):
            for fidelity in ('Balanced','Faithful','Off'):
                for first in (False, True):
                    cost = uga._palette_cost_cpu(rgb, np.asarray(palette)[ids],
                                                 perceptual=perceptual, fidelity=fidelity)
                    pos = np.argmin(cost, axis=-1)
                    expected = ids[pos]
                    if first:
                        cc = np.where(custom[ids], cost, np.inf)
                        cp = np.argmin(cc, axis=-1)
                        expected = np.where(cc.min(axis=-1)<=cost.min(axis=-1)*1.06+.0006,ids[cp],expected)
                    (actual, visible), _ = uga.palette_indices_rgba(
                        Image.fromarray(raw), palette, ids, custom, gpu_mode='CPU',
                        color_rendering='Perceptual match' if perceptual else 'RGB nearest',
                        color_fidelity=fidelity, custom_mode='Custom colors first' if first else 'Calibrated palette')
                    np.testing.assert_array_equal(actual, expected)
                    np.testing.assert_array_equal(visible, (raw[...,3]>0)&(rgb.min(axis=-1)<245))

    def test_near_black_bytes_do_not_become_white(self):
        image = Image.new('RGB', (2,2), (1,1,1))
        (out,_),_ = uga.palette_indices_rgba(image, [(0,0,0),(1,1,1),(255,255,255)],
                                             range(3), [], gpu_mode='CPU')
        self.assertTrue(np.all(out==1))

    def test_memory_bound_for_wide_images(self):
        real = uga._palette_cost_cpu
        shapes=[]
        def capture(src, pal, **kw):
            shapes.append((len(src),len(pal)))
            return real(src,pal,**kw)
        with patch.object(uga,'_palette_cost_cpu',side_effect=capture):
            uga.palette_indices_rgba(Image.new('RGB',(12000,1)), [(i,i,i) for i in range(100)],
                                      range(100), [], gpu_mode='CPU')
        self.assertTrue(shapes)
        self.assertTrue(all(n<=4096 and p<=32 for n,p in shapes))

    def test_cancelled_and_empty_palette(self):
        with self.assertRaises(InterruptedError):
            uga.palette_indices_rgba(Image.new('RGB',(1,1)), [(0,0,0)], [0], [],
                                      cancelled=lambda:True)
        with self.assertRaises(ValueError):
            uga.palette_indices_rgba(Image.new('RGB',(1,1)), [], [], [], gpu_mode='CPU')


class MotorOptimizationTests(unittest.TestCase):
    def test_tall_region_uses_fewer_turns_without_losing_pixels(self):
        group=[(20,y,24,y) for y in range(10,350)]
        paths, meta=build_fast_paths([group],{})
        before=Image.new('1',(64,380));after=before.copy()
        d=ImageDraw.Draw(before)
        for a,b,c,e in group:d.line((a,b,c,e),fill=1)
        d=ImageDraw.Draw(after)
        for path in paths[0]:d.line(path,fill=1)
        self.assertEqual(before.tobytes(),after.tobytes())
        self.assertEqual(meta['lossless_axis_reoriented_colors'],1)
        self.assertLess(meta['ordered_cost_after_seconds'],meta['ordered_cost_before_seconds'])

    def test_reorientation_preserves_holes_reversed_runs_and_outline(self):
        rng=np.random.default_rng(19)
        for _ in range(20):
            group=[(0,0,4,4)]+[(8,y,3,y) for y in range(2,150) if rng.random()>.1]
            alternate=_vertical_alternative(group,1,lambda:False)
            if alternate is None:continue
            self.assertEqual(alternate[0],group[0])
            masks=[]
            for runs in (group,alternate):
                im=Image.new('1',(16,160));d=ImageDraw.Draw(im)
                for run in runs:d.line(run,fill=1)
                masks.append(im.tobytes())
            self.assertEqual(*masks)

    def test_identical_candidates_reuse_cost(self):
        _,meta=build_fast_paths([[(1,y,60,y) for y in range(20)]],{})
        self.assertGreater(meta['duplicate_candidate_evaluations_skipped'],0)


class ScalarKernelTests(unittest.TestCase):
    """Validate the exact kernel scalar math with a native C++ compiler.

    This is not a CUDA device test; hardware execution is separately optional.
    """
    def test_scalar_kernel_against_numpy_reference(self):
        compiler=shutil.which('g++')
        if not compiler:self.skipTest('C++ compiler unavailable')
        source = '#include <cmath>\n#include <iostream>\n#include <vector>\nusing namespace std;\n'
        source += PREAMBLE.replace('__device__','')
        source += '''
int main(){
 int n,count,perceptual,fidelity,custom_first;
 cin>>n>>count>>perceptual>>fidelity>>custom_first;
 vector<float> rgb(n*3),palette(count*3),lab(count*3);
 vector<short> ids(count); vector<int> custom(count);
 for(auto &v:rgb)cin>>v; for(auto &v:palette)cin>>v; for(auto &v:lab)cin>>v;
 for(auto &v:ids)cin>>v; for(auto &v:custom)cin>>v;
 for(int i=0;i<n;++i){short result;
'''+OPERATION+'\ncout<<result<<" ";}}'
        rng=np.random.default_rng(55)
        rgb=rng.integers(0,256,(128,3)).astype(np.float32)
        pal=rng.integers(0,256,(67,3)).astype(np.float32)
        pal[33]=pal[0];rgb[0]=pal[0]
        lab=uga._oklab_cpu(pal/255)
        ids=np.arange(len(pal),dtype=np.int16)
        flags=(ids%3==0).astype(np.uint8)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'kernel.cpp';path.write_text(source)
            exe=Path(tmp)/'kernel'
            subprocess.run([compiler,'-O2','-ffp-contract=off',str(path),'-o',str(exe)],check=True,capture_output=True)
            for perceptual in (0,1):
                for fidelity in (0,1,2):
                    for first in (0,1):
                        data=f'128 67 {perceptual} {fidelity} {first}\n'
                        for a in (rgb,pal,lab,ids,flags):data+=' '.join(map(str,a.ravel()))+'\n'
                        actual=np.fromstring(subprocess.run([str(exe)],input=data,text=True,capture_output=True,check=True).stdout,sep=' ',dtype=np.int16)
                        cost=uga._palette_cost_cpu(rgb,pal,perceptual=perceptual,fidelity=('Off','Balanced','Faithful')[fidelity])
                        expected=cost.argmin(axis=-1)
                        if first:
                            cc=np.where(flags,cost,np.inf)
                            expected=np.where(cc.min(axis=-1)<=cost.min(axis=-1)*1.06+.0006,cc.argmin(axis=-1),expected)
                        np.testing.assert_array_equal(actual,expected)

    def test_opencl_device_palette_tiles_and_edge_borders(self):
        try:
            uga._opencl_context('opencl:0:0')
        except Exception as exc:
            self.skipTest(f'OpenCL GPU unavailable: {exc}')
        rng=np.random.default_rng(299)
        image=Image.fromarray(rng.integers(0,256,(257,509,4),dtype=np.uint8))
        pal=rng.integers(0,256,(70,3)).tolist()
        flags=[i%3==0 for i in range(70)]
        for rendering in ('RGB nearest','Perceptual match'):
            expected,_=uga.palette_indices_rgba(image,pal,range(70),flags,gpu_mode='CPU',
                color_rendering=rendering,color_fidelity='Faithful',custom_mode='Custom colors first')
            route=uga.RouteInfo('palette_match','palette_match','opencl:0:0','OpenCL','GPU','GPU',True,257*509)
            with patch.object(uga,'select_route',return_value=route):
                actual,meta=uga.palette_indices_rgba(image,pal,range(70),flags,
                    color_rendering=rendering,color_fidelity='Faithful',custom_mode='Custom colors first')
            self.assertTrue(meta['accelerated'],meta)
            for a,b in zip(actual,expected):np.testing.assert_array_equal(a,b)
        for shape in ((1,7),(7,1),(5,7)):
            lum=rng.random(shape,dtype=np.float32)
            expected,_=uga.edge_magnitude(lum,gpu_mode='CPU')
            with patch.object(uga,'select_route',return_value=route):
                actual,meta=uga.edge_magnitude(lum)
            self.assertTrue(meta['accelerated'],meta)
            np.testing.assert_allclose(actual,expected,atol=1e-6)

    def test_cuda_device_matches_reference(self):
        try:
            import cupy as cp
            if not cp.cuda.runtime.getDeviceCount():self.skipTest('No CUDA device')
        except ImportError:self.skipTest('CuPy unavailable')
        except Exception as exc:self.skipTest(f'CUDA unavailable: {exc}')
        rng=np.random.default_rng(777)
        rgb=rng.integers(0,256,(32,48,3)).astype(np.float32)
        pal=rng.integers(0,256,(70,3)).astype(np.float32)
        ids=np.arange(70,dtype=np.int16);flags=(ids%3==0).astype(np.uint8)
        for perceptual in (False,True):
            for fidelity in (0,1,2):
                cost=uga._palette_cost_cpu(rgb,pal,perceptual=perceptual,fidelity=('Off','Balanced','Faithful')[fidelity])
                cc=np.where(flags,cost,np.inf)
                expected=np.where(cc.min(axis=-1)<=cost.min(axis=-1)*1.06+.0006,cc.argmin(axis=-1),cost.argmin(axis=-1))
                actual=match(cp,rgb,pal,uga._oklab_cpu(pal/255),ids,flags,perceptual=perceptual,
                             fidelity=fidelity,custom_first=True,cancelled=lambda:False)
                np.testing.assert_array_equal(actual,expected)


if __name__=='__main__':unittest.main()
