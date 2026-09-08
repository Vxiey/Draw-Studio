import tempfile
import unittest
from pathlib import Path

from PerformanceAutoTuner import build_recommendation, load_tune_result, save_tune_result, format_tune_summary


class PerformanceAutoTunerTests(unittest.TestCase):
    def test_high_end_cuda_recommendation(self):
        rec = build_recommendation(
            scheduler_result={"logical_cpus": 32, "recommended_workers": 16, "best_score": 9.5},
            available_mb=28000,
            gpu_result={"used_gpu": True, "accelerated": True, "device": "RTX", "total_vram_mb": 16384,
                        "free_vram_mb": 15000, "throughput_mp_s": 20.0},
        )
        self.assertEqual(rec.cpu_workers, "Auto")
        self.assertEqual(rec.cpu_workers_effective, 16)
        self.assertEqual(rec.resource_scheduler, "Benchmark recommendations")
        self.assertEqual(rec.gpu_mode, "NVIDIA CUDA")
        self.assertEqual(rec.gpu_vram, "75%")
        self.assertEqual(rec.planning_resolution, "Extreme")
        self.assertLessEqual(int(rec.ram_custom_mb), 12288)

    def test_cpu_fallback_is_safe(self):
        rec = build_recommendation(
            scheduler_result={"logical_cpus": 8, "recommended_workers": 6, "best_score": 2.0},
            available_mb=5000,
            gpu_result={"used_gpu": False, "accelerated": False, "device": "CPU"},
        )
        self.assertEqual(rec.gpu_mode, "CPU")
        self.assertEqual(rec.gpu_vram, "Auto")
        self.assertIn(rec.planning_resolution, ("Standard", "High"))
        self.assertNotEqual(rec.resource_scheduler, "Off")

    def test_result_round_trip_and_summary(self):
        payload = {"version": 1, "elapsed_ms": 123.0, "recommendation": {
            "cpu_workers_effective": 8, "logical_cpus": 16, "ram_budget": "4 GB",
            "gpu_available": False, "gpu_device": "CPU", "gpu_vram": "Auto", "planning_resolution": "High"
        }}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tune.json"
            save_tune_result(payload, path)
            loaded = load_tune_result(path)
            self.assertEqual(loaded["recommendation"]["planning_resolution"], "High")
            self.assertIn("CPU 8/16", format_tune_summary(loaded))


if __name__ == "__main__":
    unittest.main()
