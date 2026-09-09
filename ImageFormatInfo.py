"""Describe decoded pixels without guessing an encoded format from a suffix."""
def image_label(image, name):
    encoded = image.info.get('draw_studio_format') or image.format or 'Clipboard / decoded pixels'
    if 'A' in image.getbands():
        low, high = image.getchannel('A').getextrema()
    elif 'transparency' in image.info:
        low, high = image.convert('RGBA').getchannel('A').getextrema()
    else:
        low, high = 255, 255
    transparency = 'transparent pixels' if low < 255 else 'no transparency'
    return f'{name} · {encoded} · {image.width} × {image.height} · {transparency}'
