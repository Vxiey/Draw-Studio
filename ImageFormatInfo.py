"""Describe decoded pixels without guessing an encoded format from a suffix."""
def image_label(image, name):
    encoded = image.info.get('draw_studio_format') or image.format or 'Clipboard / decoded pixels'
    alpha = image.convert('RGBA').getchannel('A')
    low, high = alpha.getextrema()
    transparency = 'transparent pixels' if low < 255 else 'no transparency'
    return f'{name} · {encoded} · {image.width} × {image.height} · {transparency}'
