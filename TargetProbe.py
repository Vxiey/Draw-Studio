"""Isolated Win32 target-window probe.

The helper reads top-level window/client geometry outside the Draw Studio GUI
process.  It supports either a selected area or an already-known HWND.
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from ctypes import wintypes
import ctypes


def emit(payload):
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def _handle_value(handle):
    try:return int(handle)
    except (TypeError,ValueError):return getattr(handle,'value',None)


def main(argv=None):
    from Colors import enable_dpi_awareness
    enable_dpi_awareness()
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--area', nargs=4, type=int, metavar=('X','Y','W','H'))
    group.add_argument('--handle', type=int)
    parser.add_argument('--exclude-pid', type=int, default=0)
    args=parser.parse_args(argv)
    try:
        from ScreenGuard import WindowMonitor
        monitor=WindowMonitor()
        if args.area is not None:
            handle,rect=monitor.capture(tuple(args.area), excluded_pids=(args.exclude_pid,))
        else:
            handle=args.handle
            monitor._validate_handle(handle)
            rect=monitor.rectangle(handle)
        handle_value=_handle_value(handle)
        if not handle_value:
            raise ValueError('Windows returned an invalid window handle.')
        client_rect=monitor.client_rectangle(handle)
        pid=wintypes.DWORD()
        monitor.api.GetWindowThreadProcessId(handle,ctypes.byref(pid))
        dpi_info=monitor.dpi_info(handle)
        emit({'ok':True,'handle':int(handle_value),'rect':[int(v) for v in rect],
              'client_rect':[int(v) for v in client_rect],'target_pid':int(pid.value),
              'dpi':int(dpi_info.dpi),'dpi_source':dpi_info.source,'dpi_scale':float(dpi_info.scale),
              'monitor_rect':list(dpi_info.monitor_rect) if dpi_info.monitor_rect else None,
              'monitor_work_rect':list(dpi_info.work_rect) if dpi_info.work_rect else None})
        return 0
    except Exception as error:
        emit({'ok':False,'error':str(error),'type':type(error).__name__})
        traceback.print_exc(file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
