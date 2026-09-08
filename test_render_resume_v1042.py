import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

import SessionRecovery as SR
from RenderResume import checkpoint_after_batch, plan_fingerprint, resolve_resume
from DrawBot import execute_plan
from test_drawbot import Mouse, NoWait


def simple_plan(resume=None, progressive=False):
    opts={
        'delay':0.0,'speed':'Fast','precision':'Normal','human_mode':'Off','paint_current_color':False,
        'strict_color_verification':False,'adaptive_color_verification':False,'brush_px':1,
        'color_order':[0,1,2], 'render_resume_state':resume,
    }
    return {
        'options':opts,
        'image':Image.new('RGB',(6,3),'white'),
        'fitted':(60,30),
        'groups':[
            [(0,0,1,0)],[(0,1,1,1)],[(0,2,1,2)]
        ],
        'execution_groups':None,
        'execution_sequence':([{'color_index':0,'path':[(0,0),(1,0)],'phase':'foundation'}] if progressive else []),
        'count':3,
        'colors':((200,10,10),(10,200,10),(10,10,200)),
        'color_selectors':(
            {'kind':'palette','palette_index':0,'rgb':(200,10,10)},
            {'kind':'palette','palette_index':1,'rgb':(10,200,10)},
            {'kind':'palette','palette_index':2,'rgb':(10,10,200)},
        ),
        'path_stats':{},
    }


class RenderResumeV1042Tests(unittest.TestCase):
    def test_checkpoint_after_two_batches_resumes_at_three(self):
        plan=simple_plan()
        state=checkpoint_after_batch(plan,2,prelude_complete=True)
        self.assertEqual(state['completed_count'],2)
        self.assertEqual(state['total_colors'],3)
        self.assertEqual(state['next_color'],3)
        resolved=resolve_resume(plan,state)
        self.assertTrue(resolved['compatible'])
        self.assertEqual(resolved['completed_count'],2)

    def test_changed_plan_fingerprint_never_skips(self):
        plan=simple_plan();state=checkpoint_after_batch(plan,2)
        changed=simple_plan();changed['colors']=((201,10,10),(10,200,10),(10,10,200))
        resolved=resolve_resume(changed,state)
        self.assertFalse(resolved['compatible'])
        self.assertEqual(resolved['completed_count'],0)

    def test_progressive_plan_rejects_batch_resume(self):
        base=simple_plan();state=checkpoint_after_batch(base,1)
        progressive=simple_plan(resume=state,progressive=True)
        resolved=resolve_resume(progressive,state)
        self.assertFalse(resolved['compatible'])
        self.assertIn('progressive',resolved['reason'])

    def test_execute_skips_completed_color_batches(self):
        base=simple_plan();state=checkpoint_after_batch(base,2)
        resumed=simple_plan(resume=state)
        mouse=Mouse();events=[];saved=[]
        execute_plan(resumed,(100,100,60,30),[(10,10),(20,10),(30,10)],mouse,NoWait(),threading.Event(),
                     lambda *e:events.append(e),checkpoint=lambda value:saved.append(value))
        # Only the third palette colour is selected; batches 1-2 are not redrawn.
        palette_clicks=sum(1 for a in mouse.actions if a==('click',))
        # one palette click + one short stroke click/drag may occur depending on zero-length mapping;
        # the palette move proves only color 3 was selected.
        palette_moves=[a for a in mouse.actions if a[0]=='move' and (a[1],a[2]) in ((10,10),(20,10),(30,10))]
        self.assertEqual(palette_moves,[('move',30,10)])
        self.assertTrue(any(k=='status' and '2/3 colors already completed' in v for k,v in events if isinstance(v,str)))
        self.assertEqual(saved[-1]['completed_count'],3)

    def test_dual_checkpoint_persists_render_progress_separately_and_never_armed_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);state_file=base/'recovery'/'session-recovery.json';image_file=base/'recovery'/'last-image.png';render_file=base/'recovery'/'render-resume.json'
            plan=simple_plan();progress=checkpoint_after_batch(plan,2)
            target_hint={'version':1,'profile':'Microsoft Paint','paint_tool':'Pencil','target_dpi':96,'drawing_area_rel':[1,2,30,40],'image_size':[8,6],'palette_required':True,'target_handle':999}
            with patch.object(SR,'RECOVERY_DIR',state_file.parent),patch.object(SR,'STATE_FILE',state_file),patch.object(SR,'IMAGE_FILE',image_file),patch.object(SR,'RENDER_FILE',render_file):
                SR.save_snapshot(profile='Microsoft Paint',options={'color_workflow':'Finish color first'},saved_area=[(1,2),(30,40)],image=Image.new('RGBA',(8,6),'red'),target_lock=target_hint)
                SR.save_render_progress(progress)
                loaded=SR.load_snapshot()
                self.assertEqual(loaded['render_resume']['completed_count'],2)
                self.assertEqual(loaded['target_lock_hint']['paint_tool'],'Pencil')
                raw=json.loads(state_file.read_text(encoding='utf-8'))
                self.assertNotIn('render_resume',raw)
                self.assertTrue(render_file.exists())
                self.assertFalse(raw['safety']['drawing_armed'])
                self.assertFalse(raw['safety']['target_lock_restored'])
                self.assertFalse(raw['safety']['preflight_restored'])
                self.assertFalse(raw['safety']['dry_run_restored'])
                self.assertFalse(raw['safety']['small_test_restored'])

    def test_corrupt_render_checkpoint_does_not_block_session_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);state_file=base/'recovery'/'session-recovery.json';image_file=base/'recovery'/'last-image.png';render_file=base/'recovery'/'render-resume.json'
            with patch.object(SR,'RECOVERY_DIR',state_file.parent),patch.object(SR,'STATE_FILE',state_file),patch.object(SR,'IMAGE_FILE',image_file),patch.object(SR,'RENDER_FILE',render_file):
                SR.save_snapshot(profile='Microsoft Paint',options={'color_workflow':'Finish color first'},saved_area=[(1,2),(30,40)],image=Image.new('RGBA',(8,6),'red'))
                render_file.write_text('{broken',encoding='utf-8')
                loaded=SR.load_snapshot()
                self.assertEqual(loaded['profile'],'Microsoft Paint')
                self.assertTrue(loaded['has_image'])
                self.assertIsNone(loaded['render_resume'])

if __name__=='__main__':unittest.main()
