import unittest
from unittest import mock
import numpy as np
from PIL import Image

import UniversalGpuAcceleration as uga
from AccuracyEvaluator import evaluate_preview
from PixelAccuratePlanner import exact_palette_map, edge_map


def profile(backend_id='cpu:numpy', backend='CPU/NumPy', vendor='CPU', device='CPU', min_pixels=0):
    prefs={}
    for name in ('oklab','palette_match','edge_map','bulk_matrix'):
        prefs[name]={
            'backend_id':backend_id,'backend':backend,'vendor':vendor,'device':device,
            'min_pixels':min_pixels,'reason':'test preference','speedup_vs_cpu':2.0,
        }
    return {'version':1,'workload_preferences':prefs,'scores_large':[]}


class Step23UniversalGpuAccelerationTests(unittest.TestCase):
    def tearDown(self):
        uga.reset_runtime_backend_health()

    def test_aliases_route_delta_quantization_and_pixel_math_through_step22_workloads(self):
        p=profile('opencl:0:0','OpenCL','AMD','Radeon')
        self.assertEqual(uga.select_route('delta_e',pixels=200000,profile=p).backend_id,'opencl:0:0')
        self.assertEqual(uga.select_route('quantization',pixels=200000,profile=p).profile_workload,'palette_match')
        self.assertEqual(uga.select_route('pixel_math',pixels=200000,profile=p).profile_workload,'bulk_matrix')

    def test_cpu_oklab_and_delta_are_deterministic(self):
        p=profile()
        rgb=np.array([[[1.0,1.0,0.0],[1.0,0.0,0.7]]],dtype=np.float32)
        lab,meta=uga.oklab_array(rgb,profile=p)
        sl,dl,de,dmeta=uga.perceptual_pair(rgb,np.flip(rgb,axis=1),profile=p)
        self.assertEqual(meta['backend_id'],'cpu:numpy')
        self.assertEqual(dmeta['backend_id'],'cpu:numpy')
        self.assertEqual(lab.shape,rgb.shape)
        self.assertGreater(float(de[0,0]),0.05)
        self.assertTrue(np.allclose(sl,lab,atol=1e-6))

    def test_palette_mapping_preserves_yellow_instead_of_pink(self):
        p=profile()
        image=Image.new('RGBA',(16,16),(255,235,0,255))
        palette=((248,220,20),(245,125,170),(190,70,45))
        (idx,mask),meta=uga.palette_indices_rgba(
            image,palette,range(3),[False,False,False],color_rendering='Perceptual match',
            color_fidelity='Faithful',gpu_mode='Auto',profile=p)
        self.assertTrue(mask.all())
        self.assertTrue(np.all(idx==0))
        self.assertEqual(meta['backend_id'],'cpu:numpy')

    def test_edge_magnitude_matches_reference(self):
        p=profile()
        lum=np.zeros((8,8),dtype=np.float32);lum[:,4:]=1.0
        out,meta=uga.edge_magnitude(lum,profile=p)
        gx=np.zeros_like(lum);gy=np.zeros_like(lum)
        gx[:,1:-1]=np.abs(lum[:,2:]-lum[:,:-2])*.5
        gy[1:-1,:]=np.abs(lum[2:,:]-lum[:-2,:])*.5
        ref=np.sqrt(gx*gx+gy*gy,dtype=np.float32)
        self.assertTrue(np.allclose(out,ref))
        self.assertEqual(meta['backend_id'],'cpu:numpy')

    def test_quantization_pairwise_oklab_is_symmetric(self):
        p=profile()
        colors=((255,255,0),(255,0,0),(0,255,0),(0,0,255))
        d,meta=uga.pairwise_oklab_distance(colors,profile=p)
        self.assertTrue(np.allclose(d,d.T,atol=1e-6))
        self.assertTrue(np.allclose(np.diag(d),0.0,atol=1e-6))
        self.assertEqual(meta['backend_id'],'cpu:numpy')

    def test_opencl_failure_is_quarantined_per_workload_and_falls_back(self):
        p=profile('opencl:0:0','OpenCL','Intel','Intel Arc')
        rgb=np.ones((512,512,3),dtype=np.float32)*.5
        with mock.patch.object(uga,'_opencl_context',side_effect=RuntimeError('driver reset')):
            out,meta=uga.oklab_array(rgb,profile=p)
        self.assertEqual(out.shape,rgb.shape)
        self.assertEqual(meta['backend_id'],'cpu:numpy')
        health=uga.backend_health_snapshot()
        self.assertTrue(any('opencl:0:0|oklab' in key for key in health))
        route=uga.select_route('oklab',pixels=rgb.shape[0]*rgb.shape[1],profile=p)
        self.assertEqual(route.backend_id,'cpu:numpy')

    def test_accuracy_evaluator_exposes_real_workload_routes(self):
        yellow=Image.new('RGB',(32,32),(255,235,0))
        pink=Image.new('RGB',(32,32),(245,125,170))
        meta=evaluate_preview(yellow,pink,gpu_mode='CPU')
        routes=meta.get('acceleration_routes') or {}
        self.assertEqual(routes['pixel_math']['backend_id'],'cpu:numpy')
        self.assertEqual(routes['delta_e_oklab']['backend_id'],'cpu:numpy')
        self.assertEqual(routes['edge_source']['backend_id'],'cpu:numpy')
        self.assertLess(meta['perceptual_color_accuracy_percent'],90.0)

    def test_pixel_accurate_planner_uses_universal_route_metadata(self):
        image=Image.new('RGB',(32,32),(250,230,0))
        idx,drawable,_rgb,meta=exact_palette_map(image,((255,230,0),(240,120,170)),gpu_mode='CPU')
        self.assertTrue(np.all(idx==0))
        self.assertTrue(drawable.all())
        self.assertEqual(meta['palette_backend_id'],'cpu:numpy')
        edges,edge_meta=edge_map(np.asarray(image,dtype=np.uint8),gpu_mode='CPU')
        self.assertEqual(edge_meta['edge_backend_id'],'cpu:numpy')
        self.assertEqual(edges.shape,(32,32))

    def test_cpu_mode_never_attempts_opencl_or_cuda(self):
        p=profile('opencl:0:0','OpenCL','AMD','Radeon')
        with mock.patch.object(uga,'_opencl_context') as clctx:
            out,meta=uga.oklab_array(np.zeros((512,512,3),dtype=np.float32),gpu_mode='CPU',profile=p)
        self.assertEqual(meta['backend_id'],'cpu:numpy')
        clctx.assert_not_called()
        self.assertEqual(out.shape,(512,512,3))


if __name__=='__main__':
    unittest.main()
