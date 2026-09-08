import tempfile
import unittest
from pathlib import Path

import ColorCache
import DrawTimeCalibration as DTC
import LayoutFingerprintV2 as LF
from CalibrationState import palette_state
from Colors import calibration_metadata, load_calibration, save_calibration
from ProfileStorage import (profile_layout_cache_file, profile_palette_file,
                            profile_settings_file, profile_timing_file,
                            profile_verified_color_file)


class Step9ProfileCalibrationIsolationTests(unittest.TestCase):
    def test_profile_storage_paths_are_distinct(self):
        paint='microsoft-paint';gartic='gartic-phone';skribbl='skribbl'
        for fn in (profile_palette_file,profile_settings_file,profile_timing_file,
                   profile_layout_cache_file,profile_verified_color_file):
            self.assertEqual(len({str(fn(paint)),str(fn(gartic)),str(fn(skribbl))}),3)

    def test_palette_file_records_profile_and_rejects_cross_profile_load(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'gartic.json'
            save_calibration([(10,10)],[(255,0,0)],path,profile_key='gartic-phone',state='calibrated')
            meta=calibration_metadata(path,profile_key='gartic-phone')
            self.assertEqual(meta['profile'],'gartic-phone')
            self.assertEqual(meta['state'],'calibrated')
            with self.assertRaises(ValueError):
                load_calibration(path,profile_key='skribbl')

    def test_palette_state_distinguishes_estimated_and_verified(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'palette.json'
            self.assertEqual(palette_state('gartic-phone',palette_path=path,preset_available=True)['state'],'estimated')
            save_calibration([(10,10)],[(255,0,0)],path,profile_key='gartic-phone',state='verified',
                             verification={'method':'test','confidence':.95})
            state=palette_state('gartic-phone',palette_path=path,preset_available=True)
            self.assertEqual(state['state'],'verified')
            self.assertAlmostEqual(state['verification']['confidence'],.95)

    def test_verified_color_cache_requires_same_profile_context_and_workflow(self):
        old=ColorCache.cache_path
        with tempfile.TemporaryDirectory() as td:
            ColorCache.cache_path=lambda profile:Path(td)/f'{profile}.json'
            try:
                ColorCache.put_verified('microsoft-paint',(250,210,20),(250,210,20),delta_e2000=0,
                                        method='numeric',context_fingerprint='ctx-a',workflow='Adaptive exact (recommended)')
                self.assertIn('FAD214',ColorCache.load_cache('microsoft-paint',context_fingerprint='ctx-a',workflow='Adaptive exact (recommended)'))
                self.assertEqual(ColorCache.load_cache('microsoft-paint',context_fingerprint='ctx-b',workflow='Adaptive exact (recommended)'),{})
                self.assertEqual(ColorCache.load_cache('microsoft-paint',context_fingerprint='ctx-a',workflow='Calibrated palette'),{})
                self.assertEqual(ColorCache.load_cache('gartic-phone',context_fingerprint='ctx-a',workflow='Adaptive exact (recommended)'),{})
            finally:
                ColorCache.cache_path=old

    def test_default_timing_storage_is_separate_per_profile(self):
        old=DTC.profile_timing_file
        with tempfile.TemporaryDirectory() as td:
            DTC.profile_timing_file=lambda profile:Path(td)/f'{profile}.json'
            try:
                paint={'profile_key':'microsoft-paint','speed':'Fast','precision':'High','brush_px':1,'paint_tool':'Pencil','custom_color_workflow':'Adaptive exact (recommended)'}
                gartic={'profile_key':'gartic-phone','speed':'Fast','precision':'High','brush_px':1,'tool_strategy':'Auto','custom_color_workflow':'Calibrated palette'}
                DTC.record_sample(paint,100,150,completed_paths=100)
                self.assertTrue(DTC.correction_for(paint)['learned'])
                self.assertFalse(DTC.correction_for(gartic)['learned'])
                self.assertNotEqual(DTC.correction_for(paint)['storage_path'],DTC.correction_for(gartic)['storage_path'])
            finally:
                DTC.profile_timing_file=old

    def test_timing_key_isolated_by_brush_tool_and_color_workflow(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'paint-time.json'
            base={'profile_key':'microsoft-paint','speed':'Fast','precision':'High','brush_px':1,'paint_tool':'Pencil','custom_color_workflow':'Adaptive exact (recommended)'}
            DTC.record_sample(base,100,140,path=path)
            self.assertTrue(DTC.correction_for(base,path=path)['learned'])
            self.assertFalse(DTC.correction_for(dict(base,brush_px=5),path=path)['learned'])
            self.assertFalse(DTC.correction_for(dict(base,paint_tool='Brush'),path=path)['learned'])
            self.assertFalse(DTC.correction_for(dict(base,custom_color_workflow='Calibrated palette'),path=path)['learned'])

    def test_release_build_collects_step9_modules(self):
        source=Path('build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'ProfileStorage'",source)
        self.assertIn("'CalibrationState'",source)
        self.assertIn("'ColorCache'",source)

    def test_layout_cache_defaults_to_profile_specific_file(self):
        old=LF.profile_layout_cache_file
        with tempfile.TemporaryDirectory() as td:
            LF.profile_layout_cache_file=lambda profile:Path(td)/f'layout-{profile}.json'
            try:
                meta={'client_rect':(100,100,900,700),'dpi':96}
                palette=[{'name':'A','position':(150,620),'rgb':(0,0,0)},
                         {'name':'B','position':(180,620),'rgb':(255,0,0)},
                         {'name':'C','position':(210,620),'rgb':(0,255,0)}]
                LF.record_layout('gartic-phone',meta,(300,180,820,580),palette)
                self.assertTrue((Path(td)/'layout-gartic-phone.json').exists())
                self.assertFalse((Path(td)/'layout-skribbl.json').exists())
                LF.record_layout('skribbl',meta,(300,180,820,580),palette)
                self.assertTrue((Path(td)/'layout-skribbl.json').exists())
                self.assertEqual({e['profile_key'] for e in LF.load_cache(Path(td)/'layout-gartic-phone.json')['entries']},{'gartic-phone'})
                self.assertEqual({e['profile_key'] for e in LF.load_cache(Path(td)/'layout-skribbl.json')['entries']},{'skribbl'})
            finally:
                LF.profile_layout_cache_file=old


if __name__=='__main__':
    unittest.main()
