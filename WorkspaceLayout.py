"""Layout decisions in logical pixels, independent of Tk and desktop input."""
def window_size(screen_width,screen_height):
    return max(480,min(1180,screen_width-60)),max(400,min(800,screen_height-90))
def compact_layout(width): return width < 1050
