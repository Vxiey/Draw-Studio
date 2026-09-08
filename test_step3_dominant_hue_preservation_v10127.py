import unittest
from PIL import Image, ImageDraw

from AdaptivePaletteFidelity import select_adaptive_palette
from DominantHuePreservation import dominant_hue_family, dominant_hue_anchors, summarize_hue_families
from DynamicColors import build_dynamic_color_strokes, _merge_quantized


class Step3DominantHuePreservationV10127Tests(unittest.TestCase):
    def test_broad_oklab_families_classify_primary_colours(self):
        self.assertEqual(dominant_hue_family((250,35,25)),'red')
        self.assertEqual(dominant_hue_family((250,220,25)),'yellow')
        self.assertEqual(dominant_hue_family((25,205,55)),'green')
        self.assertEqual(dominant_hue_family((25,70,235)),'blue')
        self.assertIsNone(dominant_hue_family((128,128,128)))

    def test_dominant_family_slots_are_selected_before_many_red_shades(self):
        palette=[
            (160,15,15),(190,25,20),(220,35,25),(245,55,35),(255,90,45),(255,125,65),
            (245,220,25),(35,190,55),(30,75,230),
            (105,95,90),(180,175,170),(245,240,235),
        ]
        # Red owns lots of shade variants, but yellow/green/blue are each large
        # objects and must get a slot at cap=4.
        weights=[12,11,10,9,8,7,24,22,20,1,1,1]
        groups=[[(0,i,round(w),i)] for i,w in enumerate(weights)]
        keep,_mapping,meta=select_adaptive_palette(groups,palette,4,fidelity='Faithful')
        families={dominant_hue_family(palette[i]) for i in keep}
        self.assertTrue({'red','yellow','green','blue'}.issubset(families))
        self.assertEqual(meta['dominant_hue_preservation_percent'],100.0)
        self.assertEqual(meta['lost_dominant_hue_families'],())
        self.assertTrue(meta['dominant_hue_preservation'])

    def test_quantized_merge_keeps_one_cluster_per_large_family(self):
        entries=[]
        colors=[
            ((235,35,25),260),((250,65,35),100),((190,25,20),90),
            ((245,220,30),230),((215,185,25),45),
            ((35,190,55),220),((55,165,65),35),
            ((30,70,230),210),((55,90,205),30),
            ((120,115,110),8),((170,165,160),7),
        ]
        for i,(rgb,count) in enumerate(colors):
            entries.append({'qindex':i,'rgb':rgb,'count':count})
        clusters,mapping=_merge_quantized(entries,4)
        self.assertEqual(len(clusters),4)
        families={dominant_hue_family(c['rgb']) for c in clusters}
        self.assertTrue({'red','yellow','green','blue'}.issubset(families))
        self.assertEqual(set(mapping),set(range(len(entries))))

    def test_dynamic_exact_integration_keeps_four_large_object_families(self):
        im=Image.new('RGB',(80,80),(245,245,245));d=ImageDraw.Draw(im)
        d.rectangle((0,0,39,39),fill=(235,40,25))
        d.rectangle((40,0,79,39),fill=(245,220,25))
        d.rectangle((0,40,39,79),fill=(35,190,55))
        d.rectangle((40,40,79,79),fill=(30,75,230))
        # Small texture shades should be expendable before an entire family.
        for x in range(0,80,8):
            d.line((x,0,x,79),fill=(min(255,110+x),45,35),width=1)
        palette=((0,0,0),(255,255,255),(235,40,25),(245,220,25),(35,190,55),(30,75,230))
        groups,rendered,selectors,meta=build_dynamic_color_strokes(
            im,palette,max_colors=4,skip_white=False,exact_available=True,
            color_fidelity='Faithful',profile_name='Microsoft Paint')
        families={dominant_hue_family(rgb) for rgb,g in zip(rendered,groups) if g}
        self.assertTrue({'red','yellow','green','blue'}.issubset(families))
        self.assertTrue(meta['dominant_hue_preservation'])
        self.assertTrue({'red','yellow','green','blue'}.issubset(set(meta['dominant_hue_families'])))

    def test_tiny_chromatic_accent_does_not_steal_guaranteed_slot(self):
        colors=[(240,40,30),(245,220,30),(35,190,55),(30,70,230),(255,0,255)]
        weights=[35,30,25,9,1]
        summaries=summarize_hue_families(colors,weights,fidelity='Faithful',max_families=4)
        names={s.family for s in summaries}
        self.assertNotIn('magenta',names)
        self.assertTrue({'red','yellow','green','blue'}.issubset(names))


if __name__=='__main__':
    unittest.main()
