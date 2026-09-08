import unittest
from PIL import Image, ImageDraw

from DynamicColors import _merge_quantized, build_dynamic_color_strokes
from RegionAwareQuantization import (
    build_region_context, cluster_region_relation, merge_threshold_multiplier,
    region_detail_anchor_candidates,
)
from ColorFidelity import oklab_metrics


class Step4RegionAwareQuantizationV10128Tests(unittest.TestCase):
    def _context(self):
        # One red object: q0 is the main body, q1 is a close low-value texture
        # stripe, q2 is a bright highlight, q3 is a dark protected micro-feature.
        labels=Image.new('L',(36,18),0)
        d=ImageDraw.Draw(labels)
        for x in range(3,33,6):
            d.rectangle((x,0,x+1,17),fill=1)
        d.rectangle((24,2,34,6),fill=2)
        d.rectangle((16,8,18,10),fill=3)
        colors={0:(190,48,38),1:(198,52,40),2:(255,160,132),3:(60,12,10)}
        src=Image.new('RGB',labels.size)
        lp=labels.load();sp=src.load()
        for y in range(labels.height):
            for x in range(labels.width):sp[x,y]=colors[int(lp[x,y])]
        import numpy as np
        flat=np.asarray(labels,dtype=np.uint8).ravel()
        counts={i:int((flat==i).sum()) for i in colors}
        entries=[{'qindex':i,'rgb':colors[i],'count':counts[i]} for i in colors]
        protected=Image.new('L',labels.size,0);pd=ImageDraw.Draw(protected);pd.rectangle((16,8,18,10),fill=255)
        return src,labels,entries,protected

    def test_same_object_close_texture_gets_positive_merge_affinity(self):
        src,labels,entries,protected=self._context()
        ctx=build_region_context(src,labels,entries,protected_mask=protected)
        rel=cluster_region_relation(entries[0],entries[1],ctx)
        self.assertTrue(rel['same_family'])
        self.assertGreater(rel['adjacency'],0.0)
        self.assertGreater(rel['texture_affinity'],0.10)
        self.assertGreater(merge_threshold_multiplier(rel),1.0)

    def test_highlight_shadow_roles_are_not_treated_as_disposable_texture(self):
        src,labels,entries,protected=self._context()
        ctx=build_region_context(src,labels,entries,protected_mask=protected)
        rel=cluster_region_relation(entries[2],entries[3],ctx)
        self.assertTrue(rel['tone_conflict'])
        self.assertLess(merge_threshold_multiplier(rel),0.6)

    def test_small_protected_feature_is_expensive_to_merge(self):
        src,labels,entries,protected=self._context()
        ctx=build_region_context(src,labels,entries,protected_mask=protected)
        rel=cluster_region_relation(entries[3],entries[0],ctx)
        self.assertTrue(rel['detail_conflict'])
        self.assertGreater(rel['region_penalty'],1.5)
        self.assertGreater(ctx['diagnostics']['protected_detail_buckets'],0)

    def test_forced_reduction_merges_texture_before_highlight_shadow(self):
        src,labels,entries,protected=self._context()
        ctx=build_region_context(src,labels,entries,protected_mask=protected)
        diag={}
        clusters,mapping=_merge_quantized(entries,3,region_context=ctx,diagnostics=diag)
        self.assertEqual(len(clusters),3)
        # q0/q1 should share a cluster; the bright and dark roles survive apart.
        self.assertEqual(mapping[0],mapping[1])
        self.assertNotEqual(mapping[2],mapping[3])
        self.assertGreaterEqual(diag['region_texture_merges'],1)
        lights=sorted(oklab_metrics(tuple(c['rgb']))[0] for c in clusters)
        self.assertGreater(lights[-1]-lights[0],35.0)

    def test_dynamic_exact_reports_region_aware_diagnostics(self):
        im=Image.new('RGB',(48,32),(205,55,38));d=ImageDraw.Draw(im)
        for x in range(0,48,6):d.line((x,0,x,31),fill=(215,62,42),width=1)
        d.rectangle((14,8,30,14),fill=(255,168,125))
        d.rectangle((20,18,24,22),fill=(55,15,12))
        palette=((0,0,0),(255,255,255),(205,55,38),(255,168,125),(55,15,12))
        groups,rendered,selectors,meta=build_dynamic_color_strokes(
            im,palette,max_colors=3,skip_white=False,exact_available=True,
            color_fidelity='Faithful',profile_name='Microsoft Paint')
        self.assertTrue(meta['region_aware_quantization'])
        self.assertTrue(meta['region_quantization']['region_aware_quantization'])
        self.assertGreaterEqual(meta['region_quantization']['region_color_buckets'],3)
        self.assertEqual(len(rendered),3)

    def test_game_palette_can_reserve_local_high_contrast_detail(self):
        # A small magenta accent shares the top-left cell with a large yellow
        # object. It is deliberately too small to become a dominant hue family,
        # but strong local contrast makes it a Step-4 detail candidate.
        groups=[[],[],[]]
        groups[0]=[(0,y,30,y) for y in range(12)]       # yellow mass
        groups[1]=[(35,y,65,y) for y in range(12)]     # green mass
        groups[2]=[(4,4,7,4),(4,5,7,5),(4,6,7,6)]      # magenta accent
        palette=[(245,220,25),(35,190,55),(230,35,180)]
        weights=[400.0,400.0,12.0]
        anchors=region_detail_anchor_candidates(groups,palette,[0,1,2],weights,10)
        self.assertIn(2,anchors)


if __name__=='__main__':
    unittest.main()
