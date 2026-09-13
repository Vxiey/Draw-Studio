from pathlib import Path


def replace_once(path,old,new):
    p=Path(path);text=p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'anchor missing in {path}: {old[:90]!r}')
    p.write_text(text.replace(old,new,1),encoding='utf-8')

# AutoDrawing: apply one style policy before preset resolution. Explicit style
# + Auto/Manual uses that profile directly; Masterpiece/Extra fast may override
# only the quality/speed dimensions they own.
replace_once('AutoDrawing.py',
"from PIL import Image\n\nPRESETS=",
"from PIL import Image\nfrom DrawingStyleProfiles import apply_drawing_style\n\nPRESETS=")
replace_once('AutoDrawing.py',
"def resolve_drawing(image,options):\n    out=dict(options);preset=out.get('render_preset','Manual')\n    if preset not in PRESETS:raise ValueError('Choose Auto, Manual, Masterpiece or Extra fast.')\n    if preset=='Manual' or out.get('auto_engine_resolved'):return out\n",
"def resolve_drawing(image,options):\n    out=apply_drawing_style(image,dict(options));preset=out.get('render_preset','Manual')\n    if preset not in PRESETS:raise ValueError('Choose Auto, Manual, Masterpiece or Extra fast.')\n    if out.get('drawing_style')!='Auto' and preset in ('Auto','Manual'):\n        out['auto_engine_resolved']=True\n        out['auto_drawing_meta']={'preset':preset,'image_kind':out.get('drawing_style_resolved'),\n            'engine':'drawing style profile','drawing_style_profile':out.get('drawing_style_meta')}\n        return out\n    if preset=='Manual' or out.get('auto_engine_resolved'):return out\n")

# DrawBot persistent/profile-scoped UI state and planner options.
replace_once('DrawBot.py',
"        self.render_preset = tk.StringVar(value='Auto')\n        self.sketch_detail = tk.StringVar(value='Auto')\n",
"        self.render_preset = tk.StringVar(value='Auto')\n        self.drawing_style = tk.StringVar(value='Auto')\n        self.sketch_detail = tk.StringVar(value='Auto')\n")
replace_once('DrawBot.py',
"            'target_stroke_custom','render_style','draw_quality','human_mode','gpu_mode','gpu_vram',",
"            'target_stroke_custom','drawing_style','render_style','draw_quality','human_mode','gpu_mode','gpu_vram',")
replace_once('DrawBot.py',
"            if hasattr(self,'render_preset'):self.render_preset.set(data.get('render_preset') if data.get('render_preset') in ('Auto','Manual','Masterpiece','Extra fast') else 'Auto')\n            if hasattr(self,'read_gartic_timer'):",
"            if hasattr(self,'render_preset'):self.render_preset.set(data.get('render_preset') if data.get('render_preset') in ('Auto','Manual','Masterpiece','Extra fast') else 'Auto')\n            if hasattr(self,'drawing_style'):\n                from DrawingStyleProfiles import DRAWING_STYLES\n                self.drawing_style.set(data.get('drawing_style') if data.get('drawing_style') in DRAWING_STYLES else 'Auto')\n            if hasattr(self,'read_gartic_timer'):")
replace_once('DrawBot.py',
"'target_stroke_custom':getattr(getattr(self,'target_stroke_custom',None),'get',lambda:'2500')(),'render_style':getattr(getattr(self,'render_style',None),'get',lambda:'Auto')(),",
"'target_stroke_custom':getattr(getattr(self,'target_stroke_custom',None),'get',lambda:'2500')(),'drawing_style':getattr(getattr(self,'drawing_style',None),'get',lambda:'Auto')(),'render_style':getattr(getattr(self,'render_style',None),'get',lambda:'Auto')(),")
replace_once('DrawBot.py',
"        if hasattr(self,'render_preset'):data['render_preset']=self.render_preset.get()\n        if hasattr(self,'read_gartic_timer'):",
"        if hasattr(self,'render_preset'):data['render_preset']=self.render_preset.get()\n        if hasattr(self,'drawing_style'):data['drawing_style']=self.drawing_style.get()\n        if hasattr(self,'read_gartic_timer'):")
replace_once('DrawBot.py',
"'render_style':render_style,'draw_quality':draw_quality,'human_mode':human_mode,",
"'drawing_style':getattr(getattr(self,'drawing_style',None),'get',lambda:'Auto')(),'render_style':render_style,'draw_quality':draw_quality,'human_mode':human_mode,")

# Profile isolation keeps each target's chosen drawing style separate.
replace_once('ProfileIsolation.py',
"'target_stroke_count', 'target_stroke_custom', 'render_style', 'hybrid_mode',",
"'target_stroke_count', 'target_stroke_custom', 'drawing_style', 'render_style', 'hybrid_mode',")

# Session recovery also preserves style selection when present.
p=Path('SessionRecovery.py');text=p.read_text(encoding='utf-8')
if '"render_style", "draw_quality"' in text and '"drawing_style", "render_style"' not in text:
    p.write_text(text.replace('"render_style", "draw_quality"','"drawing_style", "render_style", "draw_quality"',1),encoding='utf-8')

# UI: style profile lives next to speed/quality preset, not target profile.
replace_once('StudioUI.py',
"from SketchFillRenderer import SKETCH_FILL_RENDER_STYLE\n",
"from SketchFillRenderer import SKETCH_FILL_RENDER_STYLE\nfrom DrawingStyleProfiles import DRAWING_STYLES\n")
replace_once('StudioUI.py',
"    preset_menu.configure(command=a.render_preset_changed)\n",
"    preset_menu.configure(command=a.render_preset_changed)\n    style_profile_menu=setting_row(step4,'Drawing style profile',a.drawing_style,DRAWING_STYLES,\n        'Auto classifies the source. Pixel Art protects exact pixels; Logo prioritizes Fill + clean regions; Portrait protects faces/details; Photo/Shaded preserves tonal structure; Line Art protects thin contours; Cartoon/Illustration uses flat regions + outlines.',width=178)\n")

# Timing learning must not mix different style profiles.
replace_once('DrawTimeCalibration.py',
"    style=_token(options.get(\"render_style\"),\"auto\")\n    return f\"{base}::mode={mode}::preset={preset}::quality={quality}::style={style}\"\n",
"    style=_token(options.get(\"render_style\"),\"auto\")\n    style_profile=_token(options.get(\"drawing_style_resolved\") or options.get(\"drawing_style\"),\"auto\")\n    return f\"{base}::mode={mode}::preset={preset}::quality={quality}::style={style}::drawing-style={style_profile}\"\n")

# Package new pure-python modules.
p=Path('build_exe.py');text=p.read_text(encoding='utf-8')
if "'DrawingStyleProfiles'" not in text:
    anchors=["'CompletedDrawingAnalysis'","\"CompletedDrawingAnalysis\""]
    for anchor in anchors:
        if anchor in text:
            quote=anchor[0]
            text=text.replace(anchor,anchor+','+quote+'DrawingStyleProfiles'+quote,1);break
    p.write_text(text,encoding='utf-8')

# Version rc28.
replace_once('Version.py',"APP_VERSION = '1.0.145-rc27'","APP_VERSION = '1.0.145-rc28'")

# Installer metadata if still rc27.
p=Path('installer/ImageDrawBot.iss');text=p.read_text(encoding='utf-8')
text=text.replace('#define MyAppVersion "1.0.145-rc27"','#define MyAppVersion "1.0.145-rc28"')
p.write_text(text,encoding='utf-8')
