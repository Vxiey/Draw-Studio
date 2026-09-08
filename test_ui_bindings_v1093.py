import builtins
from pathlib import Path
import symtable
import unittest

class UINameBindingTests(unittest.TestCase):
    def test_ui_modules_have_no_undefined_global_references(self):
        root=Path(__file__).resolve().parent
        for filename in ('StudioUI.py','PreviewDeck.py','ResponsiveRows.py','SmoothScroll.py','WorkspaceLayout.py','ScreenTaskWindow.py'):
            with self.subTest(module=filename):
                table=symtable.symtable((root/filename).read_text(encoding='utf-8'),filename,'exec')
                defined={s.get_name() for s in table.get_symbols() if s.is_assigned() or s.is_imported() or s.is_namespace()}
                defined.update(dir(builtins));defined.update(('__name__','__file__','__package__'))
                errors=[]
                def walk(scope):
                    for symbol in scope.get_symbols():
                        if symbol.is_global() and symbol.is_referenced() and symbol.get_name() not in defined:
                            errors.append(scope.get_name()+': '+symbol.get_name())
                    for child in scope.get_children():walk(child)
                walk(table)
                self.assertEqual(errors,[],filename)
