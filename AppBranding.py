"""One visual identity for Tk windows, taskbar grouping and the app header."""
import sys

from RuntimePaths import resource_path

APP_USER_MODEL_ID = 'Vxiey.ImageDrawBot'
ICON_PNG = 'assets/image-draw-bot-icon.png'
ICON_ICO = 'assets/image-draw-bot-icon.ico'


def set_windows_app_id():
    """Call before creating windows; source launches should not group as Python."""
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except (AttributeError, OSError):
        pass


def configure_root(root):
    """Apply the same artwork to this Tcl interpreter and future toplevels.

    Images are retained on their own root, never in a process-global Tk cache.
    Failure to load decorative artwork must not prevent starting the app.
    """
    if getattr(root, '_image_draw_bot_branding', False):
        return root
    try:
        from PIL import Image, ImageTk
        with Image.open(resource_path(ICON_PNG)) as image:
            root._image_draw_bot_icons = tuple(
                ImageTk.PhotoImage(image.resize((n,n), Image.Resampling.LANCZOS), master=root)
                for n in (16,32,48,64,128,256))
        root.iconphoto(True, *root._image_draw_bot_icons)
    except Exception:
        return root
    ico = resource_path(ICON_ICO)

    def apply(window):
        try:
            if not window.winfo_exists():
                return
            if sys.platform == 'win32' and ico.is_file():
                # CTk's override also records that its default icon must not win.
                window.iconbitmap(str(ico))
            else:
                window.iconphoto(False, *root._image_draw_bot_icons)
        except Exception:
            pass

    def mapped(event):
        window = event.widget
        try:
            if window.winfo_toplevel() != window or getattr(window, '_image_draw_bot_icon_set', False):
                return
            window._image_draw_bot_icon_set = True
            apply(window)
            # CustomTkinter also schedules its default Windows icon at startup.
            window.after(300, lambda: apply(window))
        except Exception:
            pass

    apply(root)
    root.after(300, lambda: apply(root))
    root.bind_all('<Map>', mapped, add='+')
    root._image_draw_bot_branding = True
    return root


def header_image(size=42):
    """Use the same high-resolution master for both CustomTkinter themes/DPI."""
    import customtkinter as ctk
    from PIL import Image
    with Image.open(resource_path(ICON_PNG)) as source:
        image = source.convert('RGBA')
    return ctk.CTkImage(light_image=image, dark_image=image, size=(size,size))
