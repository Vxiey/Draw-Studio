import json
import tempfile
import unittest
from pathlib import Path
from RuntimeSafetyReport import latest_report, compact_summary

class RuntimeSafetyUiTests(unittest.TestCase):
    def test_latest_report_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            payload={'completed':True,'mode':'dry-run','profile':'Microsoft Paint','counts':{'drawn':7,'clipped':2,'skipped':1,'edge_follow':3,'blocked':0}}
            (root/'ImageDrawBot-Safety-20260906-000000-000-dry-run.json').write_text(json.dumps(payload),encoding='utf-8')
            loaded=latest_report(root)
            self.assertEqual(loaded['profile'],'Microsoft Paint')
            summary=compact_summary(loaded)
            self.assertIn('PASS',summary); self.assertIn('Clipped 2',summary); self.assertIn('Edge-follow 3',summary)

    def test_empty_summary_is_actionable(self):
        self.assertIn('Fast Dry run',compact_summary(None))

if __name__=='__main__': unittest.main()
