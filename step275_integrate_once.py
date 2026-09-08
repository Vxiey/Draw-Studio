from pathlib import Path


def replace_once(path, old, new):
    p=Path(path);text=p.read_text(encoding='utf-8')
    if old not in text:
        raise RuntimeError(f'Patch anchor missing in {path}: {old[:120]!r}')
    text=text.replace(old,new,1);p.write_text(text,encoding='utf-8')


def insert_before(path, marker, block):
    p=Path(path);text=p.read_text(encoding='utf-8')
    if marker not in text:raise RuntimeError(f'Insert marker missing in {path}: {marker!r}')
    text=text.replace(marker,block+marker,1);p.write_text(text,encoding='utf-8')

# DrawBot: session-only state next to the existing browser setup status.
replace_once('DrawBot.py',
"        self.browser_auto_text = tk.StringVar(value='Browser Auto Setup is waiting for a supported game profile and target canvas.')\n        self.browser_one_click_text = tk.StringVar(value='One-Click: choose a supported browser game and add an image. Canvas, palette, brush and preflight run automatically.')\n",
"        self.browser_auto_text = tk.StringVar(value='Browser Auto Setup is waiting for a supported game profile and target canvas.')\n        self.browser_one_click_text = tk.StringVar(value='One-Click: choose a supported browser game and add an image. Canvas, palette, brush and preflight run automatically.')\n        self.one_click_setup_text = tk.StringVar(value='One-click Setup: select Microsoft Paint or a supported browser game to auto-detect and independently verify canvas + palette.')\n        self.one_click_setup_verify_pending = None\n        self.one_click_setup_verify_payload = None\n        self.one_click_setup_after = None\n")

methods=r'''    def run_one_click_setup_verify(self):
        """Step 27.5: setup + independent live verification without drawing."""
        if self.activity or self.closing:return False
        from OneClickSetupVerification import setup_mode
        profile_name=self.game.get();profile_key=PROFILES.get(profile_name,('',))[0]
        mode=setup_mode(profile_key)
        if mode=='manual':
            self.one_click_setup_text.set('One-click Setup is unavailable for this target. Use the existing manual canvas/palette calibration controls.')
            self.status.set('This target does not have a verified One-click Setup detector. Manual calibration remains available.')
            return False
        # Setup/verification is configuration-only. Revoke every input authorization
        # before any screenshot/window activation work starts.
        mouse=getattr(self,'mouse',None)
        if hasattr(mouse,'disarm_input'):
            try:mouse.disarm_input()
            except (OSError,RuntimeError):pass
        DrawBotApp._disarm_manual_drop_in(self,'Step 27.5 One-click Setup')
        DrawBotApp._disarm_full_draw(self,'Step 27.5 One-click Setup',update_text=True)
        DrawBotApp._cancel_after_attr(self,'one_click_setup_after')
        self.one_click_setup_verify_pending={'profile_name':profile_name,'profile_key':profile_key,'mode':mode}
        self.one_click_setup_verify_payload=None
        self.one_click_setup_text.set('One-click Setup running · read-only target/canvas/palette scan · no drawing input.')
        self.status.set(f'One-click Setup: preparing {profile_name}… No mouse or keyboard input will be sent.')
        if mode=='paint':
            started=bool(self.auto_calibrate_paint_tools(one_click_verify=True))
            if not started:self.one_click_setup_verify_pending=None
            return started
        current_handle=(self.target_window[0] if getattr(self,'target_window',None) else None)
        palette_path=Path(self.calibration_path)
        def work():
            try:
                from BrowserOneClick import one_click_setup
                payload=one_click_setup(profile_name,profile_key,palette_path,current_handle=current_handle)
                payload['one_click_setup_verify_only']=True
                self.events.put(('browser_one_click_setup_complete',payload))
            except Exception as error:
                self.events.put(('one_click_setup_verification_complete',{
                    'passed':False,'profile_key':profile_key,'mode':'browser','confidence':0.0,
                    'canvas_ok':False,'palette_ok':False,'palette_verified':0,'palette_tested':0,
                    'tool_ok':False,'reasons':[str(error)],'error':str(error),'profile_name':profile_name,
                }))
        started=bool(self.begin_worker('browser-one-click-setup',work))
        if not started:self.one_click_setup_verify_pending=None
        return started

    def _queue_one_click_setup_verification(self, setup_payload):
        pending=getattr(self,'one_click_setup_verify_pending',None)
        if not isinstance(pending,dict):return False
        if pending.get('profile_name')!=self.game.get():
            self.one_click_setup_verify_pending=None;self.one_click_setup_verify_payload=None
            return False
        self.one_click_setup_verify_payload=dict(setup_payload or {})
        DrawBotApp._cancel_after_attr(self,'one_click_setup_after')
        try:self.one_click_setup_after=self.root.after(80,self._start_one_click_setup_verification)
        except (tk.TclError,RuntimeError):self.one_click_setup_after=None;return False
        self.one_click_setup_text.set('Initial setup found. Running an independent live canvas/palette verification pass…')
        return True

    def _start_one_click_setup_verification(self):
        self.one_click_setup_after=None
        pending=getattr(self,'one_click_setup_verify_pending',None)
        payload=getattr(self,'one_click_setup_verify_payload',None)
        if not isinstance(pending,dict) or not isinstance(payload,dict) or self.closing:return False
        if pending.get('profile_name')!=self.game.get():
            self.one_click_setup_verify_pending=None;self.one_click_setup_verify_payload=None
            return False
        if self.activity:
            try:self.one_click_setup_after=self.root.after(80,self._start_one_click_setup_verification)
            except (tk.TclError,RuntimeError):self.one_click_setup_after=None
            return True
        profile_name=str(pending['profile_name']);profile_key=str(pending['profile_key']);mode=str(pending['mode'])
        meta=dict(payload.get('target_meta') or {})
        canvas=payload.get('canvas_box')
        if not meta.get('handle') or not meta.get('rect') or not meta.get('client_rect') or not isinstance(canvas,(list,tuple)) or len(canvas)!=4:
            self.events.put(('one_click_setup_verification_complete',{
                'passed':False,'profile_key':profile_key,'mode':mode,'confidence':0.0,'canvas_ok':False,
                'palette_ok':False,'palette_verified':0,'palette_tested':0,'tool_ok':False,
                'reasons':['setup did not return complete target/canvas metadata'],'profile_name':profile_name,
            }))
            return False
        palette_path=Path(self.calibration_path)
        def work():
            try:
                from ScreenGuard import WindowMonitor
                from PIL import ImageGrab
                monitor=WindowMonitor();handle=int(meta['handle']);target=(handle,tuple(meta['rect']))
                if not monitor.activate(target):raise ValueError('Windows could not activate the verified target for the second read-only check.')
                if self.stop.wait(.18):raise InterruptedError('One-click Setup verification cancelled.')
                current_rect=tuple(monitor.rectangle(handle));client=tuple(monitor.client_rectangle(handle));dpi=monitor.dpi(handle)
                live_meta=dict(meta);live_meta.update({'handle':handle,'rect':current_rect,'client_rect':client,'dpi':dpi})
                shot=ImageGrab.grab(bbox=client,all_screens=True).convert('RGB')
                from OneClickSetupVerification import verify_browser_live,verify_paint_live
                if mode=='browser':
                    result=verify_browser_live(profile_key,live_meta,canvas,palette_path,screenshot=shot)
                else:
                    result=verify_paint_live(live_meta,canvas,palette_path,screenshot=shot)
                out=result.as_dict();out['profile_name']=profile_name;out['target_meta']=live_meta
                self.events.put(('one_click_setup_verification_complete',out))
            except InterruptedError:raise
            except Exception as error:
                self.events.put(('one_click_setup_verification_complete',{
                    'passed':False,'profile_key':profile_key,'mode':mode,'confidence':0.0,'canvas_ok':False,
                    'palette_ok':False,'palette_verified':0,'palette_tested':0,'tool_ok':False,
                    'reasons':[str(error)],'error':str(error),'profile_name':profile_name,
                }))
        return bool(self.begin_worker('one-click-verify',work))

'''
insert_before('DrawBot.py','    def auto_calibrate_paint_tools(self):\n',methods)

# Let the existing Paint worker report setup failures cleanly to Step 27.5.
replace_once('DrawBot.py',
"    def auto_calibrate_paint_tools(self):\n        \"\"\"Visually detect safe Paint toolbar controls without generating input.\"\"\"\n        if self.activity:return\n",
"    def auto_calibrate_paint_tools(self, *, one_click_verify=False):\n        \"\"\"Visually detect safe Paint toolbar controls without generating input.\"\"\"\n        if self.activity:return False\n")
replace_once('DrawBot.py',
"        def work():\n            from TargetCapture import probe_handle_isolated\n            from PaintFullCalibration import choose_paint_window,detect_setup,save_setup\n",
"        def work():\n            try:\n                from TargetCapture import probe_handle_isolated\n                from PaintFullCalibration import choose_paint_window,detect_setup,save_setup\n",)
# Indent the rest of the Paint worker via bounded block rewrite.
p=Path('DrawBot.py');text=p.read_text(encoding='utf-8')
start=text.index("        def work():\n            try:\n                from TargetCapture import probe_handle_isolated\n                from PaintFullCalibration import choose_paint_window,detect_setup,save_setup\n", text.index('    def auto_calibrate_paint_tools'))
end=text.index("        self.status.set('Scanning Paint canvas, 20 palette colours and tools… No drawing clicks are sent.')",start)
block=text[start:end]
lines=block.splitlines(True)
# First two logical levels are already correct; lines after the imported save_setup line need one extra indent inside try.
try_line_index=3
for i in range(try_line_index,len(lines)):
    if lines[i].strip():lines[i]='    '+lines[i]
block=''.join(lines)
block += "            except Exception as error:\n                if one_click_verify:\n                    self.events.put(('one_click_setup_verification_complete',{'passed':False,'profile_key':'microsoft-paint','mode':'paint','confidence':0.0,'canvas_ok':False,'palette_ok':False,'palette_verified':0,'palette_tested':0,'tool_ok':False,'reasons':[str(error)],'error':str(error),'profile_name':self.game.get()}))\n                    return\n                raise\n"
text=text[:start]+block+text[end:]
p.write_text(text,encoding='utf-8')
replace_once('DrawBot.py',
"        self.status.set('Scanning Paint canvas, 20 palette colours and tools… No drawing clicks are sent.')\n        self.begin_worker('paint-auto-calibration',work)\n",
"        self.status.set('Scanning Paint canvas, 20 palette colours and tools… No drawing clicks are sent.')\n        return bool(self.begin_worker('paint-auto-calibration',work))\n")

# Successful setup events hand off to the second independent verification pass.
replace_once('DrawBot.py',
"            self.status.set('Paint ready: canvas, 20 colours, Pencil and Fill calibrated. Set Pencil to 1 px in Paint and run Small test.')\n",
"            self.status.set('Paint ready: canvas, 20 colours, Pencil and Fill calibrated. Set Pencil to 1 px in Paint and run Small test.')\n            if isinstance(getattr(self,'one_click_setup_verify_pending',None),dict):\n                DrawBotApp._queue_one_click_setup_verification(self,dict(value or {}))\n")
replace_once('DrawBot.py',
"                log_event(f'Browser One-Click setup completed: profile={profile_name!r} colors={count} confidence={confidence:.3f} canvas={canvas!r} force={force}.')\n        elif kind=='browser_auto_calibration_complete':\n",
"                log_event(f'Browser One-Click setup completed: profile={profile_name!r} colors={count} confidence={confidence:.3f} canvas={canvas!r} force={force}.')\n                if isinstance(getattr(self,'one_click_setup_verify_pending',None),dict):\n                    DrawBotApp._queue_one_click_setup_verification(self,payload)\n        elif kind=='one_click_setup_verification_complete':\n            payload=value if isinstance(value,dict) else {}\n            profile_name=str(payload.get('profile_name') or self.game.get())\n            pending=getattr(self,'one_click_setup_verify_pending',None)\n            if profile_name!=self.game.get() or (isinstance(pending,dict) and pending.get('profile_name')!=profile_name):\n                log_event('Ignored stale Step 27.5 One-click Setup verification result after profile change.')\n            else:\n                from OneClickSetupVerification import format_verification\n                passed=bool(payload.get('passed'))\n                self.one_click_setup_text.set(format_verification(payload))\n                if passed:\n                    confidence=float(payload.get('confidence',0) or 0)\n                    if str(payload.get('mode'))=='browser':self.browser_auto_calibration_success=True\n                    self.status.set(f'✓ One-click Setup verified for {profile_name}: live canvas + palette checks passed at {confidence*100:.0f}% confidence. No drawing input was sent.')\n                    log_event(f'Step 27.5 One-click Setup PASS: profile={profile_name!r} mode={payload.get(\"mode\")!r} confidence={confidence:.3f} canvas={payload.get(\"canvas_ok\")} palette={payload.get(\"palette_verified\")}/{payload.get(\"palette_tested\")} tools={payload.get(\"tool_ok\")}.')\n                else:\n                    if str(payload.get('mode'))=='browser':self.browser_auto_calibration_success=False\n                    reason='; '.join(str(x) for x in (payload.get('reasons') or ())) or str(payload.get('error') or 'verification failed')\n                    DrawBotApp._invalidate_target_lock(self,'Step 27.5 verification failed',disarm=True)\n                    DrawBotApp._invalidate_safety_preflight(self,'Step 27.5 verification failed',disarm=True)\n                    self.status.set(f'One-click Setup blocked safely: {reason} Use manual calibration if the target layout changed.')\n                    log_event(f'Step 27.5 One-click Setup BLOCKED: profile={profile_name!r} reason={reason!r}. No drawing input was sent.')\n            self.one_click_setup_verify_pending=None;self.one_click_setup_verify_payload=None\n        elif kind=='browser_auto_calibration_complete':\n")

# UI: one primary setup button, keeping target-specific controls as fallbacks.
replace_once('StudioUI.py',
"    step3 = step_card(3, 'Prepare target app', 'Browser One-Click can discover canvas/palette automatically; manual calibration is fallback only.', '🧰')\n    a.gartic_setup_button=btn(step3,'Auto setup Gartic — full canvas',a.auto_setup_gartic_full,height=35)\n",
"    step3 = step_card(3, 'Prepare target app', 'One-click Setup detects and independently verifies canvas/palette; manual calibration remains fallback.', '🧰')\n    a.one_click_setup_button=btn(step3,'⚡  One-click Setup + Verify',a.run_one_click_setup_verify,True,height=39)\n    a.one_click_setup_button.pack(fill='x',pady=(0,5))\n    tooltip(a.one_click_setup_button,'Step 27.5: Microsoft Paint and supported browser games. Detect/reuse the target, calibrate canvas/palette, then run a second independent live verification pass. Setup never starts drawing or unlocks mouse input.')\n    a.one_click_setup_label=label(step3,var=a.one_click_setup_text,muted=True,wraplength=270,size=9)\n    a.one_click_setup_label.pack(anchor='w',pady=(0,7))\n    a.gartic_setup_button=btn(step3,'Auto setup Gartic — full canvas',a.auto_setup_gartic_full,height=35)\n")

# Profile reset must clear all Step 27.5 session state so nothing leaks to another profile.
replace_once('ProfileIsolation.py',
"    app.browser_auto_calibration_success=False\n    if hasattr(app,'browser_auto_text'):app.browser_auto_text.set('Run Auto setup for this profile.')\n",
"    app.browser_auto_calibration_success=False\n    app.one_click_setup_verify_pending=None\n    app.one_click_setup_verify_payload=None\n    if hasattr(app,'one_click_setup_after'):app.one_click_setup_after=None\n    if hasattr(app,'one_click_setup_text'):app.one_click_setup_text.set('One-click Setup: select Microsoft Paint or a supported browser game to auto-detect and independently verify canvas + palette.')\n    if hasattr(app,'browser_auto_text'):app.browser_auto_text.set('Run Auto setup for this profile.')\n")

# Screenshot verification worker hides Draw Studio just like the existing setup workers.
replace_once('ScreenTaskWindow.py',
"SCREEN_ACTIVITIES=frozenset(('calibration','exact-color-calibration','browser-auto-calibration',\n    'browser-one-click-setup','paint-auto-calibration','screen','record'))\n",
"SCREEN_ACTIVITIES=frozenset(('calibration','exact-color-calibration','browser-auto-calibration',\n    'browser-one-click-setup','paint-auto-calibration','one-click-verify','screen','record'))\n")

# Frozen build: module is dynamically imported from UI/runtime methods.
replace_once('build_exe.py',
"        '--hidden-import', 'BrowserVisualPreflight',\n        '--hidden-import', 'LayoutFingerprintV2',\n",
"        '--hidden-import', 'BrowserVisualPreflight',\n        '--hidden-import', 'OneClickSetupVerification',\n        '--hidden-import', 'LayoutFingerprintV2',\n")

# Version and roadmap; Step 28–30 numbering is intentionally untouched.
Path('Version.py').write_text("APP_NAME = 'Draw Studio'\nAPP_VERSION = '1.0.126-beta'\nFILE_VERSION = \"1.0.126\"\nBUILD_CHANNEL = 'beta'\n",encoding='utf-8')
replace_once('ROADMAP-STEP22-PLUS.md',
"## Step 28 — More Drawing Targets\n",
"## Completed — Step 27.5 — One-click Setup + Automatic Canvas/Palette Verification\n\nA unified read-only setup action now reuses the existing Paint/Browser detectors, discovers or reuses the target, writes only verified calibration state, then performs a second independent live canvas/palette verification pass. Failure blocks setup safely and falls back to manual calibration. It never unlocks or starts drawing.\n\n## Step 28 — More Drawing Targets\n")

print('Step 27.5 source integration prepared.')
