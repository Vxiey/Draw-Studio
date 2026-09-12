from pathlib import Path

p=Path('test_preview_quality_v104.py')
text=p.read_text(encoding='utf-8')
old="        self.assertEqual(result['cpu_workers_resolved'],1)\n"
new=("        self.assertGreaterEqual(result['cpu_workers_resolved'],1)\n"
     "        self.assertLessEqual(result['cpu_workers_resolved'],4)\n")
if old not in text:
    raise SystemExit('Expected legacy single-worker preview assertion not found')
p.write_text(text.replace(old,new,1),encoding='utf-8')
