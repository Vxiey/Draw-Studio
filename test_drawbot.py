"""Run: python -m unittest discover -s . -p test_drawbot.py -v"""
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from Colors import allColors,load_positions
from PixelData import build_strokes,prepare_image
from DrawBot import make_plan,execute_plan,load_image,DrawBotApp
from ScreenGuard import GuardedMouse


class NoWait:
    def __init__(self):self.stopped=False
    def is_set(self):return self.stopped
    def wait(self,seconds):return self.stopped


class Mouse:
    def __init__(self):self.position=(0,0);self.held=False;self.actions=[];self.fail=False
    def get_position(self):return self.position
    def move(self,x,y):
        if self.fail:raise OSError('Disconnected')
        self.position=(x,y);self.actions.append(('move',x,y))
    def click(self):self.actions.append(('click',))
    def press(self):self.held=True;self.actions.append(('press',))
    def release(self):self.held=False;self.actions.append(('release',))


class Monitor:
    def __init__(self):self.valid=True
    def verify(self,target,point):
        if not self.valid:raise InterruptedError('Wrong window')


def options():return dict(detail=10,delay=.01,lines=True,skip_white=True,contrast=1,outline=False)


class Tests(unittest.TestCase):
    def test_transparent_gaps_and_last_pixel(self):
        image=Image.new('RGBA',(5,2),(0,0,0,0))
        for x in (0,1,3,4):image.putpixel((x,0),(0,0,0,255))
        image.putpixel((4,1),(255,0,19,255))
        groups=build_strokes(image)
        self.assertEqual(groups[0],[(0,0,1,0),(3,0,4,0)])
        self.assertEqual(groups[10],[(4,1,4,1)])

    def test_empty_and_cancelled(self):
        im=Image.new('RGBA',(8,8),'white')
        self.assertEqual(sum(map(len,build_strokes(im))),0)
        self.assertIsNone(build_strokes(im,cancelled=lambda:True))

    def test_aspect(self):
        image,fitted=prepare_image(Image.new('RGBA',(400,200)),(300,300),10)
        self.assertEqual(image.size,(200,100));self.assertEqual(fitted,(300,150))

    def test_contrast_and_outline_preserve_transparency(self):
        plan=make_plan(Image.new('RGBA',(20,20),(0,0,0,0)),(40,40),dict(options(),outline=True))
        self.assertEqual(plan['count'],0)

    def test_complete_and_single_palette_click(self):
        plan=make_plan(Image.new('RGBA',(4,2),'black'),(40,20),options())
        mouse=Mouse();events=[]
        execute_plan(plan,(100,100,40,20),[(10,i) for i in range(18)],mouse,NoWait(),threading.Event(),lambda *e:events.append(e))
        self.assertFalse(mouse.held)
        self.assertEqual(sum(a[0]=='click' for a in mouse.actions),1)
        self.assertIn(('progress',(plan['count'],plan['count'])),events)
        self.assertTrue(events[-1][1].startswith('Finished'))

    def test_stop_before_start_has_no_clicks(self):
        plan=make_plan(Image.new('RGBA',(4,2),'black'),(40,20),options())
        mouse=Mouse();stop=NoWait();stop.stopped=True
        with self.assertRaises(InterruptedError):
            execute_plan(plan,(0,0,40,20),[(0,0)]*18,mouse,stop,threading.Event(),lambda *a:None)
        self.assertEqual(mouse.actions,[('release',)])

    def test_cancel_during_drag_releases_button(self):
        mouse=Mouse();stop=NoWait()
        original_press=mouse.press
        def press():original_press();stop.stopped=True
        mouse.press=press
        plan=make_plan(Image.new('RGBA',(8,1),'black'),(80,10),options())
        with self.assertRaises(InterruptedError):
            execute_plan(plan,(0,0,80,10),[(0,0)]*18,mouse,stop,threading.Event(),lambda *a:None)
        self.assertFalse(mouse.held)

    def test_pause_has_no_clicks_until_resumed(self):
        plan=make_plan(Image.new('RGBA',(4,1),'black'),(40,10),options())
        mouse=Mouse();paused=threading.Event();paused.set()
        def report(kind,value):
            if kind=='status' and value.startswith('Paused'):
                self.assertFalse(any(a[0] in ('click','press') for a in mouse.actions))
                paused.clear()
        execute_plan(plan,(0,0,40,10),[(0,0)]*18,mouse,NoWait(),paused,report)
        self.assertFalse(mouse.held)

    def test_foreground_change_blocks_input(self):
        mouse=Mouse();monitor=Monitor();guard=GuardedMouse(mouse,monitor,1)
        monitor.valid=False
        with self.assertRaises(InterruptedError):guard.move(20,20)
        self.assertEqual(mouse.actions,[])

    def test_manual_mouse_movement_blocks_click(self):
        mouse=Mouse();guard=GuardedMouse(mouse,Monitor(),1)
        guard.move(20,20);mouse.position=(500,500)
        with self.assertRaises(InterruptedError):guard.click()
        self.assertFalse(mouse.held)

    def test_image_loading_does_not_draw(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'image.png';Image.new('RGBA',(3,2),'red').save(path)
            with patch('DrawBot.execute_plan') as execute:
                im=load_image(path);self.assertEqual(im.size,(3,2));execute.assert_not_called()

    def test_invalid_positions_leave_state_unchanged(self):
        before=[(c.x,c.y) for c in allColors]
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'positions.txt';path.write_text('1\n2\n')
            with self.assertRaises(ValueError):load_positions(path)
        self.assertEqual(before,[(c.x,c.y) for c in allColors])

    def test_draw_ignores_second_start(self):
        app=DrawBotApp.__new__(DrawBotApp);app.activity='draw';app.closing=False
        with patch('DrawBot.load_calibration') as load:
            app.draw(user_initiated=True);load.assert_not_called()


if __name__=='__main__':unittest.main()
