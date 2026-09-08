"""Coalesced pointer-local scrolling for CustomTkinter panels."""
import math

class ScrollAccumulator:
    def __init__(self):self.pending=0.0
    def add(self,steps):self.pending=max(-12.0,min(12.0,self.pending+steps))
    def take(self):
        units=math.trunc(self.pending)
        self.pending-=units
        return units

def install_scrolling(root):
    state={'canvas':None,'job':None,'delta':ScrollAccumulator()}
    def flush():
        state['job']=None
        canvas=state['canvas'];units=state['delta'].take()
        try:
            if canvas is not None and canvas.winfo_exists() and units:
                canvas.yview_scroll(units,'units')
        except Exception:
            state['canvas']=None;state['delta']=ScrollAccumulator()
    def wheel(event):
        if getattr(event,'state',0)&4:return None  # Ctrl-wheel belongs to other controls.
        try:widget=root.winfo_containing(event.x_root,event.y_root)
        except Exception:return None
        canvas=None
        while widget is not None:
            # Native text/list widgets already implement their own class binding.
            if widget.winfo_class() in ('Text','Listbox','Menu'):return None
            candidate=getattr(widget,'_parent_canvas',None)
            if candidate is not None:
                canvas=candidate;break
            widget=getattr(widget,'master',None)
        if canvas is None:return None
        if state['canvas'] is not canvas:
            state['canvas']=canvas;state['delta']=ScrollAccumulator()
        number=getattr(event,'num',None)
        steps=-1 if number==4 else 1 if number==5 else -float(getattr(event,'delta',0))/120
        state['delta'].add(steps)
        if state['job'] is None:state['job']=root.after(16,flush)
        return 'break'
    # Replace CTk's per-scrollframe bind_all handlers with one dispatcher.
    # This is installed once after the complete workspace is constructed.
    for sequence in ('<MouseWheel>','<Button-4>','<Button-5>'):
        root.bind_all(sequence,wheel)
    return state
