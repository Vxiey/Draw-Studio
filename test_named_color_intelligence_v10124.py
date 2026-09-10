import unittest
from PIL import Image

from Colors import allColors, normalize_rgb
from NamedColorIntelligence import (
    color_family, describe_color_mapping, nearest_named_color,
    resolve_named_color, vocabulary_stats,
)
from DynamicColors import build_dynamic_color_strokes


class NamedColorIntelligenceTests(unittest.TestCase):
    def test_static_vocabulary_is_broad_and_deduplicated(self):
        stats=vocabulary_stats()
        self.assertEqual(stats['css4_aliases'],148)
        self.assertGreaterEqual(stats['tk_x11_aliases'],750)
        self.assertLess(stats['extended_unique_rgb'],stats['tk_x11_aliases'])
        self.assertGreater(stats['all_lookup_keys'],600)

    def test_css_tk_alias_normalization(self):
        expected=(72,61,139)
        self.assertEqual(resolve_named_color('DarkSlateBlue'),expected)
        self.assertEqual(resolve_named_color('dark slate blue'),expected)
        self.assertEqual(resolve_named_color('dark_slate_blue'),expected)
        self.assertEqual(resolve_named_color('dark-slate-blue'),expected)
        self.assertEqual(resolve_named_color('gray42'),resolve_named_color('grey42'))

    def test_compatibility_typos_are_aliases_not_canonical_names(self):
        self.assertEqual(normalize_rgb('agua'),normalize_rgb('aqua'))
        self.assertEqual(normalize_rgb('crymson'),normalize_rgb('crimson'))
        self.assertNotIn(nearest_named_color(normalize_rgb('aqua'))['name'].casefold(),('agua','crymson'))

    def test_parser_extends_without_breaking_legacy_argb(self):
        self.assertEqual(normalize_rgb('#abc'),(170,187,204))
        self.assertEqual(normalize_rgb('rgb(17,34,51)'),(17,34,51))
        self.assertEqual(normalize_rgb('rgba(255,0,0,0.5)'),(255,127,127))
        self.assertEqual(normalize_rgb('argb(128,255,0,0)'),(255,127,127))
        # Existing 8-digit Image Draw Bot semantics remain AARRGGBB.
        self.assertEqual(normalize_rgb('#80112233'),(136,144,153))

    def test_named_input_never_expands_render_palette(self):
        count=len(allColors)
        self.assertEqual(normalize_rgb('DodgerBlue'),(30,144,255))
        self.assertEqual(len(allColors),count)

    def test_nearest_name_uses_oklab_and_family_uses_numeric_color(self):
        match=nearest_named_color((26,141,249))
        self.assertEqual(match['name'],'DodgerBlue')
        self.assertLess(match['delta_e_oklab'],2.0)
        self.assertEqual(color_family((26,141,249)),'blue')
        self.assertEqual(color_family((128,128,128)),'gray')

    def test_human_mapping_diagnostics(self):
        info=describe_color_mapping((26,141,249),(0,80,205))
        self.assertEqual(info['source_name'],'DodgerBlue')
        self.assertEqual(info['source_family'],'blue')
        self.assertEqual(info['mapped_family'],'blue')
        self.assertGreater(info['delta_e_oklab'],0)
        self.assertIn('blue family',info['note'])

    def test_dynamic_color_meta_contains_named_diagnostics_only(self):
        im=Image.new('RGB',(4,1)); im.putdata([(26,141,249)]*4)
        palette=((0,80,205),(255,0,0),(255,255,255))
        groups,colors,selectors,meta=build_dynamic_color_strokes(
            im,palette,max_colors=1,skip_white=False,exact_available=False)
        self.assertTrue(meta['named_color_intelligence'])
        self.assertTrue(meta['named_color_mappings'])
        row=meta['named_color_mappings'][0]
        self.assertEqual(row['source_name'],'DodgerBlue')
        self.assertIn('mapped_name',row)
        self.assertEqual(len(colors),1)


if __name__=='__main__':
    unittest.main()
