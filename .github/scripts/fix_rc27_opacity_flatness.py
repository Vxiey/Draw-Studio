from pathlib import Path
p=Path('GarticOpacity.py')
text=p.read_text(encoding='utf-8')
old='    palette = sample.quantize(colors=32, method=Image.Quantize.MEDIANCUT)\n'
new='    palette_source = rgb.resize((w, h), Image.Resampling.NEAREST)\n    palette = palette_source.quantize(colors=32, method=Image.Quantize.MEDIANCUT)\n'
if old not in text:
    raise SystemExit('rc27 opacity palette anchor missing')
text=text.replace(old,new,1)
old="""    elif smooth >= .72 and edge <= .12 and color >= .45:
        selected = 30
        reason = \"very smooth tonal image: lower opacity can approximate gradients\"
"""
new="""    elif color <= .18:
        selected = 100
        reason = \"few-color/flat-shape source is more accurate with opaque ink\"
    elif smooth >= .72 and edge <= .12 and color >= .45:
        selected = 30
        reason = \"very smooth tonal image: lower opacity can approximate gradients\"
"""
if old not in text:
    raise SystemExit('rc27 opacity flat-shape gate anchor missing')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
