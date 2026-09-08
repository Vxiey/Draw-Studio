import unittest

from TargetCapabilities import (
    all_capabilities, auto_browser_profile_keys, browser_profile_keys,
    capability_for_key, manual_browser_profile_keys, requires_manual_setup,
    supports_one_click_setup,
)


class Step28TargetCapabilityTests(unittest.TestCase):
    def test_keys_are_unique(self):
        caps=all_capabilities()
        self.assertEqual(len(caps),len({c.key for c in caps}))
        self.assertEqual(len(caps),len({c.name for c in caps}))

    def test_verified_auto_browser_set_stays_explicit(self):
        self.assertEqual(auto_browser_profile_keys(),frozenset({
            'gartic-phone','skribbl','skribbl-fast','sketchheads','sketchful'
        }))

    def test_manual_browser_targets_are_not_silently_promoted(self):
        manual=manual_browser_profile_keys()
        self.assertTrue({'drawize','gartic-io','kleki','magma'} <= manual)
        self.assertFalse(manual & auto_browser_profile_keys())

    def test_step28_new_targets_are_isolated_manual_profiles(self):
        for key in ('kleki','magma'):
            cap=capability_for_key(key)
            self.assertTrue(cap.kind.startswith('browser-'))
            self.assertEqual(cap.setup_mode,'manual')
            self.assertEqual(cap.palette_mode,'manual')
            self.assertTrue(cap.layout_fingerprint)
            self.assertTrue(cap.timing_cache)
            self.assertTrue(requires_manual_setup(key))
            self.assertFalse(supports_one_click_setup(key))

    def test_browser_target_registry_includes_all_browser_profiles(self):
        self.assertTrue({
            'gartic-phone','skribbl','skribbl-fast','sketchheads','sketchful',
            'drawize','gartic-io','kleki','magma'
        } <= browser_profile_keys())

    def test_paint_keeps_one_click_but_is_not_browser(self):
        self.assertTrue(supports_one_click_setup('microsoft-paint'))
        self.assertNotIn('microsoft-paint',browser_profile_keys())

    def test_unknown_profile_fails_to_manual_generic_capability(self):
        cap=capability_for_key('custom-abc')
        self.assertEqual(cap.setup_mode,'manual')
        self.assertEqual(cap.palette_mode,'manual')
        self.assertTrue(cap.layout_fingerprint)
        self.assertTrue(cap.timing_cache)


if __name__=='__main__':
    unittest.main()
