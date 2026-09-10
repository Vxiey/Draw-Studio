import tempfile,unittest
from pathlib import Path
from PIL import Image,ImageDraw
from PaintFullCalibration import detect_setup,save_setup,choose_paint_window,resolve_manual_canvas_override
from PaintTools import build_tool_actions,load_tool_calibration

class PaintFullTests(unittest.TestCase):
    def screenshot(self):
        im=Image.new('RGB',(1920,1048),(241,243,245))
        with Image.open(Path(__file__).parent/'tests/fixtures/paint-light-ribbon.png') as ribbon:im.paste(ribbon,(0,60))
        ImageDraw.Draw(im).rectangle((75,225,1844,995),fill='white')
        return im

    def test_detect_and_screen_offsets(self):
        r=detect_setup(self.screenshot(),(-1920,40))
        self.assertEqual(r['palette_count'],20)
        self.assertEqual(len(set(r['rgbs'])),20)
        self.assertEqual(r['tools']['Fill'],(-1612,128))
        self.assertEqual(r['canvas_box'],(-1835,275,-85,1026))
        self.assertEqual(r['canvas_visibility'],'full')
        self.assertEqual(r['canvas_clipped_edges'],[])
        self.assertEqual(r['canvas_source'],'auto-detected')

    def test_manual_canvas_override_is_authoritative(self):
        box=(140,310,860,760)
        r=detect_setup(self.screenshot(),canvas_box_override=box)
        self.assertEqual(r['canvas_box'],box)
        self.assertEqual(r['canvas_visibility'],'manual-selected')
        self.assertEqual(r['canvas_source'],'manual-selection')
        self.assertEqual(r['canvas_clipped_edges'],[])
        self.assertGreaterEqual(r['confidence'],.95)

    def test_manual_canvas_override_rejects_toolbar_or_outside_window(self):
        im=self.screenshot()
        for box in ((100,80,800,600),(-20,300,800,700),(100,300,2000,700)):
            with self.assertRaises(ValueError):detect_setup(im,canvas_box_override=box)

    def test_manual_canvas_rebases_only_same_window_same_client_size(self):
        old=(0,20,1920,1048);cur=(30,50,1950,1078);corners=[(100,300),(800,700)]
        self.assertEqual(resolve_manual_canvas_override(corners,7,old,7,cur),(130,330,830,730))
        self.assertIsNone(resolve_manual_canvas_override(corners,7,old,8,cur))
        self.assertIsNone(resolve_manual_canvas_override(corners,7,old,7,(30,50,2050,1078)))
        self.assertIsNone(resolve_manual_canvas_override([(1,1)],7,old,7,cur))

    def test_clipped_canvas_uses_safe_visible_viewport(self):
        im=self.screenshot()
        ImageDraw.Draw(im).rectangle((0,225,1919,1047),fill='white')
        r=detect_setup(im)
        self.assertEqual(r['canvas_visibility'],'viewport-clipped')
        self.assertEqual(set(r['canvas_clipped_edges']),{'left','right','bottom'})
        l,t,rr,b=r['canvas_box']
        self.assertGreater(l,0)
        self.assertGreater(t,225)
        self.assertLess(rr,im.width)
        self.assertLess(b,im.height)
        self.assertGreater(rr-l,im.width*.90)
        self.assertGreater(b-t,im.height*.70)
        self.assertGreaterEqual(r['confidence'],.85)

    def test_right_bottom_clipped_canvas_is_accepted(self):
        im=self.screenshot()
        ImageDraw.Draw(im).rectangle((75,225,1919,1047),fill='white')
        r=detect_setup(im)
        self.assertEqual(r['canvas_visibility'],'viewport-clipped')
        self.assertEqual(set(r['canvas_clipped_edges']),{'right','bottom'})
        self.assertGreater(r['canvas_box'][0],75)
        self.assertLess(r['canvas_box'][2],im.width)
        self.assertLess(r['canvas_box'][3],im.height)

    def test_compact_visible_canvas_is_accepted(self):
        im=self.screenshot();d=ImageDraw.Draw(im)
        d.rectangle((75,225,1844,995),fill=(241,243,245));d.rectangle((700,280,1120,720),fill='white')
        r=detect_setup(im)
        self.assertEqual(r['canvas_visibility'],'viewport-compact')
        l,t,rr,b=r['canvas_box']
        self.assertGreater(l,700);self.assertGreater(t,280);self.assertLess(rr,1120);self.assertLess(b,720)
        self.assertGreater(rr-l,350);self.assertGreater(b-t,350);self.assertGreaterEqual(r['confidence'],.85)

    def test_edge_resize_handle_does_not_split_blank_canvas(self):
        im=self.screenshot();d=ImageDraw.Draw(im);d.rectangle((930,988,990,995),fill=(190,190,190))
        r=detect_setup(im)
        self.assertGreater(r['canvas_box'][2]-r['canvas_box'][0],1600)
        self.assertGreater(r['canvas_box'][3]-r['canvas_box'][1],700)

    def test_light_border_segment_does_not_false_ambiguous(self):
        im=self.screenshot();d=ImageDraw.Draw(im)
        d.rectangle((69,300,74,500),fill='white')
        r=detect_setup(im)
        self.assertEqual(r['canvas_visibility'],'full')
        self.assertGreater(r['canvas_box'][2]-r['canvas_box'][0],1600)

    def test_indistinguishable_white_halo_is_inset_safely(self):
        im=self.screenshot();d=ImageDraw.Draw(im)
        # Pure white adjacent to the document is indistinguishable from canvas in
        # a screenshot. Auto detection may envelope it, but the conservative
        # visible-edge inset must keep the final drawable boundary inside the
        # known document edge rather than drawing into the halo.
        d.rectangle((69,225,74,995),fill='white')
        for y in range(225,996,50):d.rectangle((69,y,74,min(995,y+1)),fill=(241,243,245))
        r=detect_setup(im)
        self.assertGreaterEqual(r['canvas_box'][0],77)
        self.assertGreater(r['canvas_box'][2]-r['canvas_box'][0],1600)

    def test_truly_tiny_visible_area_is_rejected(self):
        im=self.screenshot();d=ImageDraw.Draw(im)
        d.rectangle((75,225,1844,995),fill=(241,243,245));d.rectangle((850,400,930,470),fill='white')
        with self.assertRaisesRegex(ValueError,'too small'):detect_setup(im)

    def test_scaled_reference(self):
        im=self.screenshot()
        for scale in (.8,1.25,1.5,2):
            r=detect_setup(im.resize((round(im.width*scale),round(im.height*scale))))
            self.assertEqual(r['palette_count'],20)
            self.assertAlmostEqual(r['tools']['Fill'][0],308*scale,delta=5)

    def test_blank_and_wrong_icons_rejected(self):
        with self.assertRaises(ValueError):detect_setup(Image.new('RGB',(1000,800),'white'))
        im=self.screenshot();ImageDraw.Draw(im).rectangle((250,70,326,146),fill=(248,249,250))
        with self.assertRaises(ValueError):detect_setup(im)

    def test_covered_palette_and_canvas_rejected(self):
        im=self.screenshot();ImageDraw.Draw(im).rectangle((825,70,875,120),fill=(240,240,240))
        with self.assertRaises(ValueError):detect_setup(im)
        im=self.screenshot();ImageDraw.Draw(im).rectangle((500,500,900,750),fill='black')
        with self.assertRaises(ValueError):detect_setup(im)

    def test_calibration_builds_real_fill_and_pencil_actions(self):
        im=self.screenshot();r=detect_setup(im)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);rect=(0,0,*im.size)
            save_setup(r,{'client_rect':rect},root/'colors.json',root/'tools.json')
            self.assertEqual(build_tool_actions('Auto (recommended)',root/'tools.json',current_client_rect=rect),[('tool',r['tools']['Pencil'])])
            self.assertEqual(build_tool_actions('Fill',root/'tools.json',current_client_rect=rect),[('tool',r['tools']['Fill'])])
            self.assertEqual(set(load_tool_calibration(root/'tools.json')['tools']),{'Pencil','Fill','Eraser'})

    def test_cancel_and_unique_window(self):
        with self.assertRaises(InterruptedError):detect_setup(self.screenshot(),cancelled=lambda:True)
        paint={'title':'Namnlös - Paint','handle':7}
        self.assertEqual(choose_paint_window([{'title':'Draw Studio'},paint]),paint)
        for windows in ([],[paint,dict(paint,handle=8)]):
            with self.assertRaises(ValueError):choose_paint_window(windows)
