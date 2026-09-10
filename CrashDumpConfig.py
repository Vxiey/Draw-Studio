"""Opt-in Windows LocalDumps configuration, with scoped backup and restoration."""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from RuntimePaths import atomic_write_text

REG_BASE = r'SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps'
VALUE_NAMES = ('DumpFolder', 'DumpCount', 'DumpType')


def restore_values(current, written, original):
    """Restore only values still matching ours; retain later external changes."""
    result=dict(current)
    for name, value in written.items():
        if result.get(name) == value:
            if name in original:result[name]=original[name]
            else:result.pop(name,None)
    return result


def configure(action, include_python=False):
    if sys.platform != 'win32':raise OSError('Windows is required for native .dmp files.')
    import ctypes
    import winreg as reg
    if not ctypes.windll.shell32.IsUserAnAdmin():
        raise PermissionError('Right-click this BAT file and choose Run as administrator once. Start Image Draw Bot normally afterwards.')
    folder=Path(os.environ['LOCALAPPDATA'])/'ImageDrawBot'/'dumps'
    folder.mkdir(parents=True,exist_ok=True)
    backup=folder/'localdumps-backup.json'
    access=reg.KEY_READ|reg.KEY_WRITE|reg.KEY_WOW64_64KEY
    state=json.loads(backup.read_text(encoding='utf-8')) if backup.exists() else {}
    if not isinstance(state,dict):raise ValueError('Invalid LocalDumps backup; no changes made.')
    def read_values(name):
        try:
            with reg.OpenKey(reg.HKEY_LOCAL_MACHINE,REG_BASE+'\\'+name,0,access) as key:
                values={}
                for value_name in VALUE_NAMES:
                    try:value,kind=reg.QueryValueEx(key,value_name);values[value_name]=[value,kind]
                    except FileNotFoundError:pass
                return values
        except FileNotFoundError:return {}
    def write_values(name,values):
        with reg.CreateKeyEx(reg.HKEY_LOCAL_MACHINE,REG_BASE+'\\'+name,0,access) as key:
            for value_name in VALUE_NAMES:
                if value_name in values:
                    value,kind=values[value_name];reg.SetValueEx(key,value_name,0,kind,value)
                else:
                    try:reg.DeleteValue(key,value_name)
                    except FileNotFoundError:pass
    if action=='enable':
        names=['ImageDrawBot.exe'] + (['python.exe','pythonw.exe'] if include_python else [])
        for name in names:
            current=read_values(name)
            if name in state:
                if current!=state[name]['written']:
                    raise RuntimeError(f'{name}: settings changed since last setup. Disable/inspect the saved configuration first.')
                continue
            written={'DumpFolder':[str(folder),reg.REG_EXPAND_SZ],
                     'DumpCount':[5,reg.REG_DWORD],'DumpType':[1,reg.REG_DWORD]}
            state[name]={'original':current,'written':written}
            # Persist undo information BEFORE touching the registry.
            atomic_write_text(backup,json.dumps(state,indent=2))
            write_values(name,written)
        return f'LocalDumps configured: {", ".join(names)}\nDump folder: {folder}\nMini dumps remain local; share them only when needed.'
    if action=='disable':
        for name, saved in list(state.items()):
            if name not in ('ImageDrawBot.exe','ImageDrawBot.exe','python.exe','pythonw.exe'):
                raise ValueError('Unexpected executable in backup; no restoration for that entry.')
            current=read_values(name)
            restored=restore_values(current,saved['written'],saved['original'])
            write_values(name,restored)
            # Keep the key itself: other tools may store additional values there.
            del state[name]
            atomic_write_text(backup,json.dumps(state,indent=2))
        return 'Image Draw Bot dump settings restored. Existing dump files were kept.'
    raise ValueError('Choose enable or disable.')


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('enable','disable'))
    parser.add_argument('--include-python',action='store_true')
    args=parser.parse_args(argv)
    if args.include_python:
        print('Source mode: this also configures crash dumps for other processes named python.exe/pythonw.exe.')
    try:
        message=configure(args.action,args.include_python);code=0
    except Exception as error:
        message=f'Dump configuration failed: {error}';code=1
    print(message)
    if getattr(sys,'frozen',False):
        from tkinter import messagebox
        (messagebox.showerror if code else messagebox.showinfo)('Crash dump setup',message)
    return code

if __name__=='__main__':raise SystemExit(main())
