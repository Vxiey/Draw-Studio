import tempfile,unittest
from pathlib import Path
from PIL import Image
from DynamicColors import build_dynamic_color_strokes,resolve_exact_color_limit
from ExactColorTools import save,load,custom_rgb_available
from CalibrationAnchors import make_anchor
from UIState import compute_workspace_state

class ColorEngineV1033Tests(unittest.TestCase):
    def test_exact_dynamic_and_palette_fallback(self):
        im=Image.new('RGB',(4,1));im.putdata([(250,10,10),(250,10,10),(10,240,10),(10,240,10)])
        palette=((255,0,0),(0,255,0),(0,0,255))
        groups,colors,selectors,meta=build_dynamic_color_strokes(im,palette,max_colors=2,skip_white=False,exact_available=True)
        self.assertEqual(len(groups),2);self.assertEqual(meta['custom_exact_colors'],1)
        self.assertEqual(meta['palette_fallback_colors'],1)
        self.assertEqual(sorted(s['kind'] for s in selectors), ['custom','palette'])
        groups2,colors2,selectors2,meta2=build_dynamic_color_strokes(im,palette,max_colors=2,skip_white=False,exact_available=False)
        self.assertTrue(all(s['kind']=='palette' for s in selectors2));self.assertEqual(set(colors2),{(255,0,0),(0,255,0)})
    def test_exact_tool_calibration_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'exact.json';anchor=make_anchor((100,200,900,800))
            controls={'OpenCustomColor':(10,10),'RedField':(20,20),'GreenField':(30,30),'BlueField':(40,40),'ConfirmColor':(50,50),'Eyedropper':(60,60)}
            save('x',controls,anchor=anchor,path=path);data=load('x',path);self.assertEqual(data['controls']['RedField'],[20,20]);self.assertTrue(custom_rgb_available('x',path))
    def test_non_paint_safety_optional_in_workspace(self):
        state=compute_workspace_state(image_loaded=True,target_name='Skribbl.io',paint_tools_ready=True,area_ready=True,palette_ready=True,test_passed=False,target_locked=False,preflight_passed=False,dry_run_passed=False,strict_safety=False)
        self.assertTrue(state.ready);items={i.key:i for i in state.items};self.assertEqual(items['dryrun'].state,'optional')
    def test_auto_limit(self):self.assertEqual(resolve_exact_color_limit('Auto',draw_quality='High likeness'),16)

    def test_exact_selector_types_rgb_with_calibrated_controls(self):
        import threading
        from DrawBot import execute_plan
        from test_drawbot import Mouse,NoWait,options
        class KB:
            def __init__(self):self.actions=[]
            def press_and_release(self,key):self.actions.append(('key',key))
            def write(self,text,delay=0):self.actions.append(('write',text))
        mouse=Mouse();mouse.calibrated_modal_click=lambda p: mouse.actions.append(('modal',*p));mouse.reset_tracking=lambda:None
        opt=options();opt['exact_color_actions']={'OpenCustomColor':(1,1),'RedField':(2,2),'GreenField':(3,3),'BlueField':(4,4),'ConfirmColor':(5,5)}
        plan={'options':opt,'image':Image.new('RGBA',(2,1)),'fitted':(20,10),'groups':[[(0,0,1,0)]],
              'execution_groups':None,'execution_sequence':[],'count':1,'colors':((12,34,56),),
              'color_selectors':({'kind':'custom','rgb':(12,34,56),'fallback_palette_index':0},)}
        kb=KB();execute_plan(plan,(100,100,20,10),[(20,20)],mouse,NoWait(),threading.Event(),lambda *a:None,keyboard=kb)
        self.assertIn(('write','12'),kb.actions);self.assertIn(('write','34'),kb.actions);self.assertIn(('write','56'),kb.actions)
        self.assertTrue(any(a[0]=='modal' for a in mouse.actions))
if __name__=='__main__':unittest.main()
