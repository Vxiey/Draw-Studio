# Color Engine — Named Color Intelligence

Draw Studio now accepts human-readable CSS4 and Tk/X11 colour names without turning those names into extra render-palette candidates.

## Runtime behavior

- Named inputs such as `red`, `DarkSlateBlue`, `dark slate blue`, `dark_slate_blue` and `dark-slate-blue` resolve to the same canonical sRGB value.
- CSS short hex is accepted: `#RGB` and `#RGBA`.
- Explicit `rgb(...)`, `rgba(...)` and `argb(...)` text forms are accepted.
- Existing Draw Studio 8-digit hex remains `AARRGGBB` for backwards compatibility.
- `gray`/`grey` and Tk/X11 aliases are normalized.
- Compatibility typos `agua` and `crymson` resolve to `aqua` and `crimson`, but are never shown as canonical names.
- Nearest human-readable names use the same OKLab distance family as the core colour engine.
- Colour-family labels are calculated numerically from OKLab hue/chroma rather than inferred from words in a name.
- Dynamic Color diagnostics record representative `source_name -> mapped_name` mappings for preview/debug output.

## Important rendering rule

The named-colour vocabulary is **diagnostics/input compatibility only**. It does not expand `Colors.allColors`, the calibrated target palette, palette reduction candidates, or Pixel Accurate planning. Rendering remains based on measured RGB, calibrated palette values and OKLab scoring.

## Static vocabulary

The source tree contains a generated static vocabulary so the packaged Windows build has no Matplotlib dependency and does not depend on whichever Tcl/Tk or X11 colour database happens to be installed on the machine.

Reference material used for the design:

- https://sites.google.com/view/paztronomer/blog/basic/python-colors
- https://inventwithpython.com/blog/complete-list-tkinter-colors-valid-and-tested.html
