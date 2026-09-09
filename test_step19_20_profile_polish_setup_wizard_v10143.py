import unittest
from pathlib import Path

from BeginnerSetupWizard import build_setup_wizard, format_setup_status, format_wizard_dialog, friendly_error_message, missing_start_requirements
from GameProfiles import profile_defaults
from ProfilePolish import apply_profile_polish, final_profile_defaults, format_profile_polish, profile_release_preset, profile_release_warnings


class Step19ProfilePolishTests(unittest.TestCase):
    def test_core_profile_release_presets_have_flows_and_warnings(self):
        for name in ("Microsoft Paint", "Gartic Phone", "Skribbl.io", "Skribbl.io Fast"):
            preset = profile_release_preset(name)
            self.assertEqual(preset.profile_name, name)
            self.assertTrue(preset.calibration_flow)
            self.assertTrue(preset.safety_flow)
            self.assertTrue(preset.warnings)
            self.assertIn("Perceptual", preset.color_policy)

    def test_release_defaults_use_game_time_budget_presets(self):
        self.assertEqual(final_profile_defaults("Gartic Phone")["time_budget_mode"], "Gartic Phone Fast")
        self.assertEqual(final_profile_defaults("Skribbl.io")["time_budget_mode"], "Skribbl Default")
        self.assertEqual(final_profile_defaults("Skribbl.io Fast")["time_budget_mode"], "Skribbl 60")
        self.assertEqual(profile_defaults("Gartic Phone")["time_budget_mode"], "Gartic Phone Fast")
        self.assertEqual(profile_defaults("Skribbl.io")["time_budget_mode"], "Skribbl Default")
        self.assertEqual(profile_defaults("Skribbl.io Fast")["time_budget_mode"], "Skribbl 60")

    def test_profile_polish_applies_only_in_auto_mode(self):
        options = {"profile_engine": "Auto", "time_budget_mode": "60 sec", "color_rendering": "RGB nearest"}
        updated, meta = apply_profile_polish("Skribbl.io", options)
        self.assertEqual(updated["time_budget_mode"], "Skribbl Default")
        self.assertEqual(updated["color_rendering"], "Perceptual match")
        self.assertTrue(meta["applied"])
        manual, manual_meta = apply_profile_polish("Skribbl.io", {"profile_engine": "Manual settings", "time_budget_mode": "60 sec"})
        self.assertEqual(manual["time_budget_mode"], "60 sec")
        self.assertFalse(manual_meta["applied"])

    def test_profile_warnings_include_estimated_palette_warning(self):
        warnings = profile_release_warnings("Gartic Phone", {"palette_state": "estimated"})
        self.assertTrue(any("Palette is not verified" in w for w in warnings))
        self.assertTrue(any("Browser One-Click" in w for w in warnings))
        self.assertIn("Profile polish:", format_profile_polish(apply_profile_polish("Gartic Phone", {"profile_engine": "Auto"})[1]))


class Step20BeginnerSetupWizardTests(unittest.TestCase):
    def test_paint_uses_automatic_preparation_without_diagnostic_gates(self):
        steps = build_setup_wizard(profile_name="Microsoft Paint", image_loaded=True)
        self.assertEqual(missing_start_requirements(steps), ())
        self.assertEqual([s.key for s in steps], ["image", "prepare", "start"])

    def test_browser_profiles_have_optional_diagnostics(self):
        steps = build_setup_wizard(profile_name="Gartic Phone", image_loaded=True, tools_ready=True,
                                   palette_ready=True, area_ready=True, full_draw_unlocked=False)
        diag = next(s for s in steps if s.key == "diagnostics")
        self.assertEqual(diag.state, "optional")
        missing = [s.key for s in missing_start_requirements(steps)]
        self.assertEqual(missing, ["unlock"])

    def test_dialog_and_friendly_errors_are_actionable(self):
        steps = build_setup_wizard(profile_name="Microsoft Paint", image_loaded=False)
        text = format_wizard_dialog(steps, profile_warnings=("warning A",))
        self.assertIn("Beginner setup wizard", text)
        self.assertIn("Profile warnings", text)
        self.assertIn("Load image", text)
        self.assertIn("Color setup needs refresh", friendly_error_message("expected color mismatch"))
        self.assertIn("Preview planning", friendly_error_message("preview timed out"))

    def test_ui_and_build_include_step19_20(self):
        ui = Path("StudioUI.py").read_text(encoding="utf-8")
        bot = Path("DrawBot.py").read_text(encoding="utf-8")
        build = Path("build_exe.py").read_text(encoding="utf-8")
        self.assertIn("Setup wizard", ui)
        self.assertIn("show_beginner_setup_wizard", bot)
        self.assertIn("ProfilePolish", build)
        self.assertIn("BeginnerSetupWizard", build)
        self.assertTrue(Path("STEP-19-FINAL-PROFILE-POLISH.md").is_file())
        self.assertTrue(Path("STEP-20-BEGINNER-SETUP-WIZARD.md").is_file())


if __name__ == "__main__":
    unittest.main()
