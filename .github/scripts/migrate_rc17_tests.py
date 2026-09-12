from pathlib import Path
p=Path('test_rc17_unified_execution_cost_eta.py')
text=p.read_text(encoding='utf-8')
old="self.assertEqual(meta['sequence_cost']['execution_cost_model'],'ExecutionCostModel')"
new="self.assertEqual(meta['sequence_operation_model']['execution_cost_model'],'ExecutionCostModel')"
if old not in text:
    raise SystemExit('Expected rc17 metadata assertion not found')
p.write_text(text.replace(old,new,1),encoding='utf-8')
