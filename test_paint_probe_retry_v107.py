import threading,unittest
from PIL import Image
from DrawBot import execute_plan
from test_adaptive_color_v1035 import AdaptiveMouse
from test_drawbot import NoWait,options

class PaintProbeRetryTests(unittest.TestCase):
    def run_case(self,recovered):
        fail={'matched':False,'actual':(207,207,207),'error':207,'confidence':19.,'sample_count':20,'reason':'weak ink'}
        ok={'matched':True,'actual':(0,0,0),'error':0,'confidence':100.,'sample_count':20,'reason':''}
        mouse=AdaptiveMouse([fail,ok if recovered else fail]);events=[]
        opt=options();opt.update(profile_name='Microsoft Paint',paint_tool='Pencil',effective_paint_tool='Pencil',
            tool_actions=[('tool',(30,30))],adaptive_color_verification=True,strict_color_verification=True,color_order=[0],brush_px=1)
        plan={'options':opt,'image':Image.new('RGBA',(20,1)),'fitted':(100,10),'groups':[[(0,0,19,0)]],
            'execution_groups':None,'execution_sequence':[],'count':1,'colors':((0,0,0),),'color_selectors':()}
        if recovered:execute_plan(plan,(100,100,100,10),[(900,900)],mouse,NoWait(),threading.Event(),lambda *e:events.append(e))
        else:
            with self.assertRaisesRegex(InterruptedError,'verification stop, not a crash'):
                execute_plan(plan,(100,100,100,10),[(900,900)],mouse,NoWait(),threading.Event(),lambda *e:events.append(e))
        self.assertEqual(len(mouse.inspect_calls),2)
        self.assertEqual(mouse.inspect_calls[0][4],mouse.inspect_calls[1][4])
    def test_retry_recovers(self):self.run_case(True)
    def test_retry_still_stops_wrong_colour(self):self.run_case(False)
