from pathlib import Path

ROOT=Path(__file__).resolve().parent

def read(name): return (ROOT/name).read_text(encoding='utf-8')
def write(name,text): (ROOT/name).write_text(text,encoding='utf-8',newline='\n')

# Source release packaging deliberately excludes runtime-generated folders. Their
# presence in an active developer/CI checkout must not make source ZIP creation
# fail as long as they are never archived. Step 30 artifact gates still reject
# any such files if they leak into a packaged Windows release.
rp=read('ReleasePackage.py')
old='NON_FATAL_EXCLUDED_DIR_NAMES = {".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".build-venv", ".venv", "venv", "build", "dist", "release"}'
new='NON_FATAL_EXCLUDED_DIR_NAMES = set(EXCLUDED_DIR_NAMES)'
if old in rp:
    rp=rp.replace(old,new,1)
elif new not in rp:
    raise RuntimeError('ReleasePackage non-fatal exclusion anchor missing')
write('ReleasePackage.py',rp)

# REAL RC FIX: select_best_release previously captured BUILD_CHANNEL in a default
# argument at import time. Resolve it at call time so tests, future channel
# transitions and in-process version/channel overrides observe current state.
up=read('UpdateCenter.py')
old='''def select_best_release(releases: Iterable[dict], *, channel: str = BUILD_CHANNEL) -> dict | None:\n    candidates = [item for item in releases if _release_allowed(item, channel)]\n'''
new='''def select_best_release(releases: Iterable[dict], *, channel: str | None = None) -> dict | None:\n    channel = BUILD_CHANNEL if channel is None else str(channel)\n    candidates = [item for item in releases if _release_allowed(item, channel)]\n'''
if old in up:
    up=up.replace(old,new,1)
elif new not in up:
    raise RuntimeError('UpdateCenter select_best_release anchor missing')
write('UpdateCenter.py',up)

# Step 12 feedback regression should learn against the strategy selected by the
# current deterministic tuner, rather than a hard-coded pre-Step25 strategy.
test=read('test_step12_auto_tuner_feedback_v10136.py')
start=test.find('    def test_tune_options_applies_learned_feedback_without_touching_pixels(self):')
end=test.find('    def test_release_build_collects_step12_module_and_doc(self):',start)
if start < 0 or end < 0:
    raise RuntimeError('Step12 feedback test anchors missing')
replacement='''    def test_tune_options_applies_learned_feedback_without_touching_pixels(self):\n        with tempfile.TemporaryDirectory() as tmp:\n            path=Path(tmp)/'feedback-gartic-phone.json'\n            options=base_options(80)\n            original_resolver=AutoTunerFeedback.profile_auto_tuner_feedback_file\n            try:\n                AutoTunerFeedback.profile_auto_tuner_feedback_file=lambda profile_key: path\n                probe=tune_options(flat_image(), options, source_kind_hint='photo / texture')\n                probe_meta=probe['auto_tuner_meta']\n                strategy=probe_meta['base_strategy']\n                source_kind=probe_meta['source_features']['source_kind']\n                for _ in range(3):\n                    result=record_completed_feedback(\n                        plan_for(options, strategy=strategy, source_kind=source_kind,\n                                 predicted=50.0, usable=80.0, visual=83.0),\n                        70.0, completed_paths=100, path=path)\n                    self.assertTrue(result['recorded'])\n                tuned=tune_options(flat_image(), options, source_kind_hint='photo / texture')\n            finally:\n                AutoTunerFeedback.profile_auto_tuner_feedback_file=original_resolver\n            feedback=tuned['auto_tuner_meta']['feedback_learning']\n            self.assertEqual(feedback['state'],'learned')\n            self.assertIn(feedback['action'],('protect-deadline','none'))\n            self.assertIn('feedback_learning', tuned['auto_tuner_meta'])\n            self.assertNotIn('_accuracy_original_source', feedback)\n\n'''
test=test[:start]+replacement+test[end:]
write('test_step12_auto_tuner_feedback_v10136.py',test)

# Step 21's documentation test should validate the current RC hardening docs,
# while still ensuring the local-only source hygiene command remains documented.
t=read('test_step21_release_cleanup_v10144.py')
t=t.replace('self.assertIn("Step 22 Universal Hardware Auto Benchmark", readme)',
            'self.assertIn("Step 30: Release Candidate Hardening", readme)')
t=t.replace('self.assertIn("STEP-22-UNIVERSAL-HARDWARE-AUTO-BENCHMARK.md", readme)',
            'self.assertIn("STEP-22-UNIVERSAL-HARDWARE-AUTO-BENCHMARK.md", readme)\n        self.assertIn("ReleaseCandidateHardening.py --source-gate", readme)')
write('test_step21_release_cleanup_v10144.py',t)

# Keep the historical Step 22 milestone phrase discoverable in the public README
# without making it the current release headline.
readme=read('README.md')
phrase='Step 22 Universal Hardware Auto Benchmark'
if phrase not in readme:
    anchor='Release architecture and roadmap references: `ROADMAP-STEP22-PLUS.md` and `STEP-22-UNIVERSAL-HARDWARE-AUTO-BENCHMARK.md`.\n'
    addition=' Historical milestone: **Step 22 Universal Hardware Auto Benchmark** introduced the universal hardware benchmark foundation.\n'
    if anchor not in readme:
        raise RuntimeError('README roadmap reference anchor missing')
    readme=readme.replace(anchor,anchor+addition,1)
write('README.md',readme)

print('Remaining Step 30 regression fixes prepared.')
