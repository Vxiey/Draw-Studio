import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from PaintPreparation import rgb_controls,prepare_controls,ensure_paint,find_control
from DrawBot import DrawBotApp


def node(name,kind='Button',rect=(10,10,30,30),value='',label=''):
    return dict(name=name,kind='ControlType.'+kind,rect=list(rect),value=value,label=label)


def dialog(language='sv'):
    names=('Röd','Grön','Blå') if language=='sv' else ('Red','Green','Blue')
    nodes=[]
    for i,name in enumerate(names):
        y=100+i*40
        nodes += [node('', 'Edit',(100,y,220,y+30),str(i*100)),node(name,'Text',(230,y,260,y+30))]
    return nodes+[node('OK',rect=(100,260,220,290)),node('Avbryt' if language=='sv' else 'Cancel',rect=(240,260,360,290))]


class PaintPreparationTests(unittest.TestCase):
    def test_rgb_swedish_and_english_label_geometry(self):
        for language in ('sv','en'):
            self.assertEqual(rgb_controls(dialog(language))['BlueField'],(160,195))

    def test_named_fields_and_negative_monitor_coordinates(self):
        nodes=dialog()
        for n in nodes:n['rect']=[v-1000 for v in n['rect']]
        self.assertEqual(rgb_controls(nodes)['RedField'],(-840,-885))

    def test_ambiguous_or_invalid_fields_rejected(self):
        nodes=dialog();nodes.append(dict(nodes[0]))
        with self.assertRaises(ValueError):rgb_controls(nodes)
        nodes=dialog();nodes[0]['value']='999'
        with self.assertRaises(ValueError):rgb_controls(nodes)

    def test_keyboard_shortcut_suffix(self):
        self.assertEqual(find_control([node('Redigera färger (Ctrl+E)')],('redigera färger',))['name'],'Redigera färger (Ctrl+E)')

    def test_prepare_captures_controls_then_cancels_dialog(self):
        main=[node('Penna'),node('Storlek','Slider',(40,40,60,200)),node('Redigera färger',rect=(80,10,100,30))]
        state={'dialog':False};actions=[]
        def backend(handle,**kw):
            if kw.get('action'):
                name=kw['element']['name'];actions.append((kw['action'],name))
                if name=='Redigera färger':state['dialog']=True
                if name=='Avbryt':state['dialog']=False
            return dialog() if state['dialog'] else main
        out=prepare_controls(42,backend=backend)
        self.assertEqual(out['OpenCustomColor'],(90,20))
        self.assertEqual(out['GreenField'],(160,155))
        self.assertEqual(actions,[('invoke','Penna'),('size','Storlek'),('invoke','Redigera färger'),('invoke','Avbryt')])
        self.assertFalse(state['dialog'])

    def test_existing_window_does_not_launch_or_clear(self):
        paint={'title':'Namnlös - Paint','handle':4}
        self.assertEqual(ensure_paint(lambda:[paint],launch=lambda:self.fail('must not launch')),paint)

    def test_missing_window_launches_once(self):
        paint={'title':'Untitled - Paint','handle':4};calls=[];windows=iter([[],[],[paint]])
        self.assertEqual(ensure_paint(lambda:next(windows),launch=lambda:calls.append('launch'),wait=lambda _:None),paint)
        self.assertEqual(calls,['launch'])

    def test_multiple_windows_and_cancel_never_launch(self):
        paint={'title':'Untitled - Paint','handle':4}
        with self.assertRaises(ValueError):ensure_paint(lambda:[paint,paint],launch=lambda:self.fail())
        with self.assertRaises(InterruptedError):ensure_paint(lambda:[],cancelled=lambda:True,launch=lambda:self.fail())

    def app(self):
        value=lambda x:SimpleNamespace(get=lambda:x)
        image=object();request={'image':image}
        return SimpleNamespace(game=value('Microsoft Paint'),original=image,paint_start_request=request,
                               activity=None,closing=False,stop=threading.Event()),request

    def test_resume_only_the_explicit_current_request(self):
        app,request=self.app()
        with patch.object(DrawBotApp,'draw',return_value=True) as draw:
            self.assertTrue(DrawBotApp._resume_prepared_paint(app,request))
            draw.assert_called_once_with(app,user_initiated=True,paint_prepared=True)
            DrawBotApp._resume_prepared_paint(app,request)
            self.assertEqual(draw.call_count,1)

    def test_cancel_image_change_profile_change_do_not_draw(self):
        for change in ('cancel','image','profile','request'):
            app,request=self.app()
            if change=='cancel':app.stop.set()
            elif change=='image':app.original=object()
            elif change=='profile':app.game=SimpleNamespace(get=lambda:'Gartic Phone')
            else:app.paint_start_request=None
            with patch.object(DrawBotApp,'draw') as draw:
                self.assertFalse(DrawBotApp._resume_prepared_paint(app,request));draw.assert_not_called()

    def test_paint_start_prepares_before_prerequisite_checks(self):
        app,_=self.app();app.auto_calibrate_paint_tools=lambda **kw:kw
        self.assertEqual(DrawBotApp.start_full_drawing(app),{'start_after':True})
        self.assertFalse(DrawBotApp._strict_safety_required(app))


class WindowsScriptSyntaxTests(unittest.TestCase):
    @unittest.skipUnless(__import__('os').name=='nt','Windows PowerShell parser')
    def test_embedded_script_parses_without_running_paint(self):
        import base64,os,subprocess
        from PaintPreparation import _SCRIPT
        payload=base64.b64encode(_SCRIPT.replace('HANDLE','42').replace('ACTION','').encode('utf-8')).decode()
        script="$s=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+payload+"'));$tokens=$null;$errors=$null;[void][System.Management.Automation.Language.Parser]::ParseInput($s,[ref]$tokens,[ref]$errors);if($errors.Count){throw ($errors | Out-String)}"
        path=os.path.join(os.environ['SystemRoot'],'System32','WindowsPowerShell','v1.0','powershell.exe')
        result=subprocess.run([path,'-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(script.encode('utf-16-le')).decode()],capture_output=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
