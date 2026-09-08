import unittest
import threading
from ScreenGuard import GuardedMouse
from test_drawbot import Mouse

class Monitor:
    def __init__(self,ready_after):self.calls=0;self.ready_after=ready_after;self.activations=0
    def activate(self,target):self.activations+=1;return False
    def active(self,target):self.calls+=1;return self.calls>self.ready_after

class FocusTests(unittest.TestCase):
    def test_waits_without_mouse_input_then_proceeds(self):
        mouse=Mouse();monitor=Monitor(4);guard=GuardedMouse(mouse,monitor,1);waits=[]
        guard.prepare_target(threading.Event(),waits.append,lambda *args:None)
        self.assertEqual(waits,[.25]*4);self.assertEqual(mouse.actions,[]);self.assertEqual(monitor.activations,1)
    def test_timeout_never_clicks(self):
        mouse=Mouse();monitor=Monitor(1000);waits=[]
        with self.assertRaisesRegex(InterruptedError,'20 seconds'):
            GuardedMouse(mouse,monitor,1).prepare_target(threading.Event(),waits.append,lambda *args:None)
        self.assertEqual(sum(waits),20);self.assertEqual(mouse.actions,[])
    def test_escape_before_activation(self):
        stop=threading.Event();stop.set();monitor=Monitor(0);mouse=Mouse()
        with self.assertRaises(InterruptedError):GuardedMouse(mouse,monitor,1).prepare_target(stop,lambda n:None,lambda *args:None)
        self.assertEqual(monitor.activations,0);self.assertEqual(mouse.actions,[])
    def test_changed_window_not_rebound(self):
        monitor=Monitor(0)
        def moved(target):raise InterruptedError('flyttats')
        monitor.activate=moved;mouse=Mouse()
        with self.assertRaisesRegex(InterruptedError,'flyttats'):
            GuardedMouse(mouse,monitor,1).prepare_target(threading.Event(),lambda n:None,lambda *args:None)
        self.assertEqual(mouse.actions,[])

if __name__=='__main__':unittest.main()
