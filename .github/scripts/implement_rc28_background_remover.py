from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def replace(path,old,new,count=1):
    p=ROOT/path;text=p.read_text(encoding='utf-8')
    if old not in text:raise SystemExit(f'rc28 anchor missing in {path}: {old[:100]!r}')
    p.write_text(text.replace(old,new,count),encoding='utf-8')

# Keep one reversible source snapshot for background removal without touching the
# normal upscale undo path.
replace('DrawBot.py',
"        self.original = self.plan = None\n        self.color_session_cache = {}\n",
"        self.original = self.plan = None\n        self.background_removal_original = None\n        self.background_removal_meta = None\n        self.color_session_cache = {}\n")

# Image actions are worker-backed so large PNGs never freeze Tk.
replace('DrawBot.py',
"""    def upscale_dialog(self):
""",
"""    def remove_image_background(self):
        if self.activity:
            self.status.set('Finish or stop the current operation before removing the background.')
            return False
        if self.original is None:
            self.status.set('Load an image before removing its background.')
            return False
        source=self.original.copy()
        if self.background_removal_original is None:
            self.background_removal_original=source.copy()
        self.status.set('Removing border-connected background…')
        log_event(f'Background removal requested: size={source.size}.')
        def work():
            from BackgroundRemoval import remove_background
            result=remove_background(source,mode='Auto',strength='Balanced',cancelled=self.stop.is_set)
            if self.stop.is_set():raise InterruptedError()
            self.events.put(('background_removed',result))
        return bool(self.begin_worker('background-remove',work))

    def undo_background_removal(self):
        if self.activity:return False
        previous=self.background_removal_original
        if previous is None:
            self.status.set('No background-removal change to undo.')
            return False
        self.original=previous.copy();self.background_removal_original=None;self.background_removal_meta=None
        self.plan=None;DrawBotApp._clear_render_resume(self,'background removal undone')
        self.file_label.set(image_label(self.original,'Background removal undone'))
        self._mark_plan_stale('Background removal undone. Build preview to update ETA.')
        self.show_previews();self._schedule_recovery_checkpoint(include_image=True,delay=40)
        self._maybe_auto_preview(delay=500,reason='background-removal-undo')
        log_event('Background removal undone.')
        return True

    def save_png_copy(self):
        if self.activity:
            self.status.set('Finish or stop the current operation before exporting PNG.')
            return False
        if self.original is None:
            self.status.set('Load an image before exporting PNG.')
            return False
        path=filedialog.asksaveasfilename(title='Save PNG',defaultextension='.png',
            filetypes=[('PNG image','*.png')])
        if not path:return False
        snapshot=self.original.copy();self.status.set('Saving PNG…')
        def work():
            from BackgroundRemoval import png_export_ready
            png_export_ready(snapshot).save(path,format='PNG',optimize=True)
            if self.stop.is_set():raise InterruptedError()
            self.events.put(('png_saved',path))
        return bool(self.begin_worker('png-export',work))

    def upscale_dialog(self):
""")

# Complete/cancel-safe event application on the UI thread.
replace('DrawBot.py',
"""        elif kind=='loaded':
            self._suppress_recovery=False
""",
"""        elif kind=='background_removed':
            result=value
            image=getattr(result,'image',None);meta=getattr(result,'metadata',{}) or {}
            if image is None:
                self.status.set('Background removal returned no image. Original preserved.')
            else:
                self.original=image.convert('RGBA');self.background_removal_meta=dict(meta);self.plan=None
                DrawBotApp._clear_render_resume(self,'background removed')
                self.file_label.set(image_label(self.original,'Background removed PNG'))
                reduction=float(meta.get('estimated_work_reduction_percent',0) or 0)
                removed=float(meta.get('removed_percent',0) or 0)
                reason=meta.get('no_op_reason')
                if reason:
                    self.status.set(f'Background remover kept the original: {reason}.')
                else:
                    self.status.set(f'Background removed: {removed:.1f}% of image area transparent; drawable pixel work reduced about {reduction:.1f}%. Build preview for real ETA.')
                log_event(f\"Background removal complete: removed={removed:.2f}% work_reduction={reduction:.2f}% ref={meta.get('reference_rgb')} threshold={meta.get('threshold')} bbox={meta.get('foreground_bbox')}.\")
                self._mark_plan_stale('Background changed. Build preview to recalculate strokes and ETA.')
                self.show_previews();self._schedule_recovery_checkpoint(include_image=True,delay=40)
                self._maybe_auto_preview(delay=500,reason='background-removed')
        elif kind=='png_saved':
            self.status.set(f'PNG saved: {value}')
            log_event(f'PNG export saved: {value!r}.')
        elif kind=='loaded':
            self._suppress_recovery=False
            self.background_removal_original=None;self.background_removal_meta=None
""")

# Compact Step 2 controls: no extra settings wall. Auto/Balanced is the safe
# default, with undo and lossless PNG export adjacent to image import.
replace('StudioUI.py',
"""    btn(row, '📋  Paste', a.paste_image, width=70, height=37).pack(side='left', padx=(6, 0))
    url_row = frame(step2)
""",
"""    btn(row, '📋  Paste', a.paste_image, width=70, height=37).pack(side='left', padx=(6, 0))
    image_tools = frame(step2); image_tools.pack(fill='x', pady=(7, 0))
    bg_btn=btn(image_tools, '✂  Remove BG', a.remove_image_background, width=104, height=34);bg_btn.pack(side='left',fill='x',expand=True)
    tooltip(bg_btn,'Auto-remove only border-connected background and convert it to transparency. Transparent pixels generate no drawing strokes.')
    undo_bg=btn(image_tools, '↶  Undo', a.undo_background_removal, width=70, height=34);undo_bg.pack(side='left',padx=(6,0))
    tooltip(undo_bg,'Restore the image from before background removal.')
    png_btn=btn(image_tools, 'PNG', a.save_png_copy, width=58, height=34);png_btn.pack(side='left',padx=(6,0))
    tooltip(png_btn,'Export the current image as a lossless RGBA PNG, preserving transparency.')
    url_row = frame(step2)
""")

# Frozen Windows build.
replace('build_exe.py',
"        '--hidden-import', 'CompletedDrawingAnalysis',\n",
"        '--hidden-import', 'CompletedDrawingAnalysis',\n        '--hidden-import', 'BackgroundRemoval',\n")

# Version continues from rc27. README download links intentionally remain on the
# last published release until rc28 artifacts exist.
replace('Version.py',"APP_VERSION = '1.0.145-rc27'","APP_VERSION = '1.0.145-rc28'")
replace('installer/ImageDrawBot.iss','#define MyAppVersion "1.0.145-rc27"','#define MyAppVersion "1.0.145-rc28"')
for p in ROOT.glob('test_*.py'):
    text=p.read_text(encoding='utf-8')
    if '1.0.145-rc27' in text:p.write_text(text.replace('1.0.145-rc27','1.0.145-rc28'),encoding='utf-8')

notes="""# Image Draw Bot v1.0.145-rc28 — Background Remover & PNG Workflow\n\n- Add **Remove BG** beside image import. It converts only border-connected background pixels to transparent alpha instead of deleting same-colour details inside the subject.\n- Transparent pixels are passed directly into the existing planners as empty canvas, so they produce no strokes and can materially reduce real drawing time.\n- Add **Undo** for the background-removal edit without interfering with the existing upscale restore path.\n- Add **PNG** export for the current RGBA image, preserving transparency.\n- Run removal and PNG encoding in cancellable workers so large source images do not freeze the UI.\n- Report removed area and approximate drawable-pixel work reduction immediately; final stroke count and ETA remain authoritative after Build preview.\n- Fail closed when the detected background would consume more than 98.5% of the image.\n"""
(ROOT/'RELEASE-NOTES-v1.0.145-rc28.md').write_text(notes,encoding='utf-8')
body=notes.split('\n\n',1)[1]
for name in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
    p=ROOT/name;p.write_text('# Image Draw Bot v1.0.145-rc28 — Background Remover & PNG Workflow\n\n'+body+'\n'+p.read_text(encoding='utf-8'),encoding='utf-8')

# Focused functional/regression tests.
test=r'''import unittest\nfrom pathlib import Path\nfrom PIL import Image,ImageDraw\nfrom BackgroundRemoval import remove_background,png_export_ready\nfrom PixelData import build_strokes\nfrom Version import APP_VERSION\n\nclass Rc28BackgroundRemovalTests(unittest.TestCase):\n    def test_version(self):self.assertEqual(APP_VERSION,'1.0.145-rc28')\n    def test_white_border_becomes_transparent_but_internal_white_survives(self):\n        im=Image.new('RGBA',(100,100),'white');d=ImageDraw.Draw(im);d.rectangle((20,20,80,80),fill=(20,20,20,255));d.rectangle((40,40,60,60),fill='white')\n        r=remove_background(im)\n        self.assertEqual(r.image.getpixel((0,0))[3],0)\n        self.assertGreater(r.image.getpixel((50,50))[3],200)\n        self.assertGreater(r.metadata['estimated_work_reduction_percent'],20)\n    def test_transparency_reduces_planner_strokes(self):\n        im=Image.new('RGBA',(80,80),'white');ImageDraw.Draw(im).rectangle((30,30,50,50),fill='black')\n        out=remove_background(im).image\n        groups=build_strokes(out,lines=True,skip_white=False)\n        count=sum(len(g) for g in groups)\n        self.assertLess(count,40)\n    def test_all_one_colour_fails_closed(self):\n        im=Image.new('RGBA',(80,80),'white');r=remove_background(im)\n        self.assertIsNotNone(r.metadata['no_op_reason']);self.assertEqual(r.image.getpixel((0,0))[3],255)\n    def test_png_export_is_rgba(self):self.assertEqual(png_export_ready(Image.new('RGB',(2,2))).mode,'RGBA')\n    def test_ui_and_worker_hooks_present(self):\n        ui=Path('StudioUI.py').read_text(encoding='utf-8');core=Path('DrawBot.py').read_text(encoding='utf-8')\n        self.assertIn('Remove BG',ui);self.assertIn('save_png_copy',core);self.assertIn("begin_worker('background-remove'",core)\n        self.assertIn("elif kind=='background_removed'",core)\n\nif __name__=='__main__':unittest.main()\n'''.replace('\\n','\n')
(ROOT/'test_rc28_background_removal.py').write_text(test,encoding='utf-8')
