"""Wrap button-only action rows when their container becomes narrow."""
def wrap_action_rows(parent):
    import customtkinter as ctk
    for child in parent.winfo_children():
        wrap_action_rows(child)
    children=[w for w in parent.winfo_children() if w is not getattr(parent,'_canvas',None)]
    if len(children)<2 or not all(isinstance(w,ctk.CTkButton) for w in children):return
    if not all(w.winfo_manager()=='pack' for w in children):return
    state={'width':None,'job':None}
    def apply():
        state['job']=None
        width=parent.winfo_width()
        signature=(width,tuple(w.winfo_reqwidth() for w in children))
        if width<=1 or signature==state['width']:return
        state['width']=signature
        for child in children:child.pack_forget();child.grid_forget()
        x=0;row=0;column=0
        for child in children:
            needed=child.winfo_reqwidth()+8
            if x and x+needed>width:row+=1;column=0;x=0
            child.grid(row=row,column=column,sticky='w',padx=3,pady=3)
            x+=needed;column+=1
    def changed(event=None):
        if event is not None and event.widget is not parent:return
        if state['job'] is None:state['job']=parent.after_idle(apply)
    parent.bind('<Configure>',changed,add='+')
    parent.after_idle(apply)
