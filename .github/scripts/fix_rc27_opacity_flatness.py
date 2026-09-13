from pathlib import Path
p=Path('GarticOpacity.py')
text=p.read_text(encoding='utf-8')
old='    palette = sample.quantize(colors=32, method=Image.Quantize.MEDIANCUT)\n'
new='    palette_source = rgb.resize((w, h), Image.Resampling.NEAREST)\n    palette = palette_source.quantize(colors=32, method=Image.Quantize.MEDIANCUT)\n'
if old not in text:
    raise SystemExit('rc27 opacity palette anchor missing')
p.write_text(text.replace(old,new,1),encoding='utf-8')
