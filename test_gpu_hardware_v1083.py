import unittest
from unittest import mock

import GpuHardware as gh
import GpuAcceleration as ga


class GpuHardwareV1083Tests(unittest.TestCase):
    def tearDown(self):
        gh._CACHE = None
        ga.reset_backend_cache()

    def test_nvidia_smi_detects_model_vram_and_driver_without_cupy(self):
        output = '0, NVIDIA GeForce RTX 5080, 16303, 591.74, 00000000:01:00.0'
        with mock.patch.object(gh, '_nvidia_smi_candidates', return_value=['nvidia-smi']), \
             mock.patch.object(gh, '_run', return_value=output):
            gpus = gh.detect_nvidia_gpus(refresh=True)
        self.assertEqual(len(gpus), 1)
        self.assertEqual(gpus[0].name, 'NVIDIA GeForce RTX 5080')
        self.assertEqual(gpus[0].memory_total_mb, 16303)
        self.assertEqual(gpus[0].driver_version, '591.74')
        self.assertEqual(gpus[0].source, 'nvidia-smi')

    def test_best_gpu_prefers_largest_vram(self):
        gh._CACHE = (
            gh.NvidiaGpu(0, 'NVIDIA RTX A', 8192, source='nvidia-smi'),
            gh.NvidiaGpu(1, 'NVIDIA RTX B', 16384, source='nvidia-smi'),
        )
        self.assertEqual(gh.best_nvidia_gpu().name, 'NVIDIA RTX B')

    def test_fallback_info_reports_detected_nvidia_when_cupy_is_unavailable(self):
        detected = gh.NvidiaGpu(0, 'NVIDIA GeForce RTX 5080', 16303, '591.74', source='nvidia-smi')
        with mock.patch.object(ga, 'best_nvidia_gpu', return_value=detected), \
             mock.patch.object(ga, '_BACKEND_CACHE', None), \
             mock.patch.object(ga, '_DISABLED_REASON', 'CuPy missing'):
            info = ga.acceleration_info('Auto')
        self.assertFalse(info.accelerated)
        self.assertTrue(info.hardware_detected)
        self.assertEqual(info.hardware_device, 'NVIDIA GeForce RTX 5080')
        self.assertEqual(info.driver_version, '591.74')

    def test_gpu_requirements_include_matched_cuda_toolkit_extra(self):
        from pathlib import Path
        text = (Path(__file__).resolve().parent / 'requirements-gpu-nvidia.txt').read_text(encoding='utf-8').lower()
        self.assertIn('cupy-cuda12x[ctk]', text)
        self.assertIn('>=14.2', text)


if __name__ == '__main__':
    unittest.main()
