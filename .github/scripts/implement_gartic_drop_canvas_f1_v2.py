from pathlib import Path

# Fix the generated regression source: the first patch script intentionally lives
# only on the validation branch, so normalize accidental doubled continuation
# slashes here instead of weakening py_compile.
p=Path('test_gartic_drop_canvas_rc25.py')
text=p.read_text(encoding='utf-8')
fixed=[]
for line in text.splitlines():
    stripped=line.rstrip()
    if stripped.endswith('\\\\'):
        # Generated source has two literal backslashes. Keep exactly one Python
        # line-continuation marker.
        line=stripped[:-1]
    fixed.append(line)
text='\n'.join(fixed)+'\n'
p.write_text(text,encoding='utf-8')

# If Gartic setup is not ready yet, Arm Drop-In should still be useful: Smart
# Canvas Drop can discover the canvas read-only, and its accepted drop then runs
# the existing forced Browser One-Click calibration/preflight before drawing.
p=Path('DrawBot.py')
text=p.read_text(encoding='utf-8')
old="""        ready,message=DrawBotApp._start_guard_ready(self,require_image=False)\n        ok,explanation=can_arm_drop_in(self.game.get(),ready=ready,message=message)\n"""
new="""        ready,message=DrawBotApp._start_guard_ready(self,require_image=False)\n        if self.game.get()=='Gartic Phone' and not ready:\n            callback=getattr(self,'arm_smart_canvas_drop',None)\n            if callable(callback):\n                self.status.set('Drop-In Start: detecting the Gartic canvas so you can drop a Google/Chrome image directly on it…')\n                log_event('Gartic Drop-In requested before setup was ready; starting read-only Smart Canvas discovery.')\n                return bool(callback())\n        ok,explanation=can_arm_drop_in(self.game.get(),ready=ready,message=message)\n"""
if old not in text:
    raise SystemExit('Gartic direct-arm marker missing')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')

# Add a focused invariant for the no-prior-setup Gartic path.
p=Path('test_gartic_drop_canvas_rc25.py')
text=p.read_text(encoding='utf-8')
marker="\nif __name__=='__main__':unittest.main()\n"
addition=r'''

class GarticDirectDropArmRc25Tests(unittest.TestCase):
    def test_arm_drop_in_can_discover_gartic_before_palette_setup(self):
        callback=mock.Mock(return_value=True)
        app=SimpleNamespace(activity=None,closing=False,game=Value('Gartic Phone'),status=Value(''),arm_smart_canvas_drop=callback)
        with mock.patch.object(DrawBotApp,'_start_guard_ready',return_value=(False,'Start locked: select the drawing area first.')):
            self.assertTrue(DrawBotApp.arm_manual_drop_in(app))
        callback.assert_called_once_with()
'''
if marker not in text:
    raise SystemExit('test footer marker missing')
text=text.replace(marker,addition+marker,1)
p.write_text(text,encoding='utf-8')
