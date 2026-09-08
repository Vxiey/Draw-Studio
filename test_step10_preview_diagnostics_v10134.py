import unittest
from PIL import Image, ImageDraw

from AccuracyEvaluator import evaluate_preview
from PreviewDiagnostics import (render_quantized_target, render_delta_e_heatmap,
                                build_preview_diagnostics, format_preview_diagnostics)
from BenchmarkSuite import run as run_benchmark_suite, format_result


class Step10PreviewDiagnosticsTests(unittest.TestCase):
    def test_quantized_target_is_separate_from_physical_brush_simulation(self):
        groups=[[(2,2,8,2)],[]]
        target=render_quantized_target((12,8),groups,((240,200,20),(220,40,50)))
        self.assertEqual(target.size,(12,8))
        self.assertEqual(target.getpixel((5,2)),(240,200,20))
        self.assertEqual(target.getpixel((5,3)),(255,255,255))

    def test_quantized_target_includes_row_span_fill(self):
        region={'color_index':0,'bbox':(1,1,8,6),'row_spans':((1,1,8),(2,1,3),(3,1,3))}
        target=render_quantized_target((10,8),[[]],((12,180,90),),fill_regions=[region])
        self.assertEqual(target.getpixel((7,1)),(12,180,90))
        self.assertEqual(target.getpixel((7,3)),(255,255,255))

    def test_delta_e_heatmap_is_zero_for_identical_and_high_for_yellow_to_pink(self):
        yellow=Image.new('RGB',(32,24),(242,200,35))
        heat0,meta0=render_delta_e_heatmap(yellow,yellow.copy())
        pink=Image.new('RGB',(32,24),(244,142,160))
        heat1,meta1=render_delta_e_heatmap(yellow,pink)
        self.assertEqual(heat0.size,yellow.size)
        self.assertLess(meta0['mean_delta_e_oklab'],1e-5)
        self.assertGreater(meta1['mean_delta_e_oklab'],0.1)
        self.assertGreater(meta1['p95_delta_e_oklab'],meta0['p95_delta_e_oklab'])
        self.assertNotEqual(heat0.getpixel((0,0)),heat1.getpixel((0,0)))

    def test_accuracy_evaluator_returns_delta_distribution_without_second_metric_pass(self):
        src=Image.new('RGB',(20,20),(245,205,30))
        dst=Image.new('RGB',(20,20),(239,135,155))
        meta=evaluate_preview(src,dst,coverage_percent=100,plan_execution_accuracy_percent=100,
                              return_error_map=True,return_delta_e_heatmap=True)
        self.assertIn('delta_e_oklab',meta)
        self.assertGreater(meta['delta_e_oklab']['mean_delta_e_oklab'],0.1)
        self.assertEqual(meta['_delta_e_heatmap_image'].size,src.size)
        self.assertEqual(meta['_error_map_image'].size,src.size)

    def test_preview_metadata_labels_calibration_accuracy_and_real_timing_separately(self):
        options={'profile_key':'gartic-phone','calibration_state':{
            'palette':{'state':'verified'},'tools':{'state':'calibrated'},'exact_color':{'state':'verified'}}}
        meta=build_preview_diagnostics(options,
            accuracy={'visual_accuracy_percent':82.5,'perceptual_color_accuracy_percent':77.2,
                      'coverage_percent':100.0,'plan_execution_accuracy_percent':100.0},
            delta_e={'mean_delta_e_oklab':.082,'p95_delta_e_oklab':.21},
            draw_time={'projected_seconds':72,'range_label':'68s–78s','confidence':'measured',
                       'estimate_source':'test','measured_samples':4},path_count=900,source_count=1600,
            performance_profile={'total_planning':1.2,'timings':{'color_planning':.7,'preview_rendering':.2}})
        text=format_preview_diagnostics(meta)
        self.assertIn('palette Verified',text)
        self.assertIn('Visual 82.5%',text)
        self.assertIn('Plan 100.0%',text)
        self.assertIn('OKLab ΔE mean 0.082',text)
        self.assertIn('900 paths',text)

    def test_benchmark_suite_is_deterministic_local_only_and_never_requires_mouse(self):
        def stub_plan(image,target,options,cancelled):
            # A deterministic fake planner lets this test verify suite orchestration
            # without any native input or expensive real planning.
            seconds=float(options['time_budget_seconds'])
            return {'count':100,'source_count':200,'colors':[(0,0,0)]*4,'estimate':seconds*.8,
                    'draw_time_estimate':{'projected_seconds':seconds*.8},
                    'options':{'deadline_render_budget_seconds':seconds*.9,
                               'adaptive_accuracy_meta':{'visual_accuracy_percent':90.0,'perceptual_color_accuracy_percent':88.0},
                               'preview_delta_e_meta':{'mean_delta_e_oklab':.05,'p95_delta_e_oklab':.12}}}
        result=run_benchmark_suite(stub_plan,{'profile_key':'test'})
        self.assertTrue(result['local_only'])
        self.assertFalse(result['mouse_input'])
        self.assertEqual(result['case_count'],4)
        self.assertEqual([r['target_seconds'] for r in result['rows']],[75,80,150,300])
        self.assertEqual(result['fit_count'],4)
        self.assertIn('4/4',format_result(result))

    def test_finish_plan_exposes_original_target_final_and_delta_layers(self):
        from DrawBot import finish_plan
        image=Image.new('RGBA',(12,8),'white')
        groups=[[(2,2,8,2)]]
        opts={'delay':.01,'speed':'Balanced','precision':'High','lines':True,
              'drawing_mode':'Smart paths (recommended)','smart_paths':True,'stroke_optimizer':'Off',
              'paint_current_color':False,'brush_px':2,'human_mode':'Off','skip_white':True,
              'plan_palette_rgb':((240,200,20),),'color_selectors':(),
              'profile_key':'test','profile_name':'Test','custom_color_workflow':'Calibrated palette',
              'calibration_state':{'profile_key':'test'},'time_budget_active':False}
        plan=finish_plan(image,(12,8),groups,opts)
        layers=plan.get('ui_previews') or {}
        self.assertIn('quantized_target',layers)
        self.assertIn('simulated_final',layers)
        self.assertIn('delta_e',layers)
        self.assertIn('accuracy_error',layers)
        self.assertIn('preview_diagnostics',plan)
        self.assertIsNot(layers['quantized_target'],layers['simulated_final'])

    def test_release_build_collects_step10_modules_and_doc(self):
        from pathlib import Path
        source=Path('build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'PreviewDiagnostics'",source)
        self.assertIn("'BenchmarkSuite'",source)
        self.assertIn('STEP-10-PREVIEW-DIAGNOSTICS-BENCHMARKS.md',source)

    def test_ui_exposes_explicit_preview_chain_and_delta_tab(self):
        from pathlib import Path
        source=Path('StudioUI.py').read_text(encoding='utf-8')
        self.assertIn("('Original', 'original_canvas')",source)
        self.assertIn("('Quantized target', 'quantized_target_canvas')",source)
        self.assertIn("('Simulated final', 'result_canvas')",source)
        self.assertIn("('ΔE heatmap', 'delta_e_canvas')",source)
        self.assertIn('Run Step 10 benchmark suite',source)


if __name__=='__main__':
    unittest.main()
