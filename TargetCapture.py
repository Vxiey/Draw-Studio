"""Safe parent-side wrappers for isolated target-window capture/inspection."""
from __future__ import annotations

import json
import os
import subprocess

from Colors import DATA_DIR
from RuntimePaths import helper_command

BASE=DATA_DIR


def _describe_exit(code):
    if code is None:return 'unknown exit code'
    unsigned=code & 0xFFFFFFFF
    known={
        0xC0000005:'Access Violation (0xC0000005)',
        0xC0000409:'Stack/fast-fail (0xC0000409)',
        0xC00000FD:'Stack overflow (0xC00000FD)',
    }
    return known.get(unsigned, f'exit code {code} / 0x{unsigned:08X}')


def _run(command, timeout=8):
    flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
    try:
        result=subprocess.run(command,cwd=BASE,capture_output=True,text=True,
                              encoding='utf-8',errors='replace',timeout=timeout,
                              creationflags=flags)
    except subprocess.TimeoutExpired as error:
        raise InterruptedError('The target-window check took too long and was stopped.') from error
    try:
        log_dir=BASE/'logs';log_dir.mkdir(parents=True,exist_ok=True)
        (log_dir/'ImageDrawBot-target-probe.log').write_text(
            f'Command: {command!r}\nExit: {result.returncode}\n\nSTDOUT:\n{result.stdout or ""}\n\nSTDERR:\n{result.stderr or ""}',
            encoding='utf-8')
    except OSError:pass
    payload=None
    for line in (result.stdout or '').splitlines():
        try:
            value=json.loads(line)
            if isinstance(value,dict):payload=value
        except (json.JSONDecodeError,TypeError):pass
    if result.returncode!=0:
        if payload and payload.get('error'):raise ValueError(payload['error'])
        raise OSError(f'The Windows target check exited unexpectedly: {_describe_exit(result.returncode)}.')
    if not payload or payload.get('ok') is not True:
        raise OSError('The Windows check returned no valid response.')
    handle=payload.get('handle');rect=payload.get('rect');client=payload.get('client_rect')
    if (not isinstance(handle,int) or not isinstance(rect,list) or len(rect)!=4 or
            not all(isinstance(v,int) for v in rect) or not isinstance(client,list) or len(client)!=4 or
            not all(isinstance(v,int) for v in client)):
        raise OSError('The Windows check returned invalid window data.')
    dpi=payload.get('dpi')
    if dpi is not None and (type(dpi) is not int or not 48<=dpi<=768):
        raise OSError('The Windows check returned invalid DPI data.')
    monitor_rect=payload.get('monitor_rect');work_rect=payload.get('monitor_work_rect')
    def optional_rect(value):
        if isinstance(value,list) and len(value)==4 and all(isinstance(v,int) for v in value):
            return tuple(value)
        return None
    return {'handle':handle,'rect':tuple(rect),'client_rect':tuple(client),
            'target_pid':payload.get('target_pid'),'dpi':dpi,
            'dpi_source':payload.get('dpi_source'),'dpi_scale':payload.get('dpi_scale'),
            'monitor_rect':optional_rect(monitor_rect),'monitor_work_rect':optional_rect(work_rect)}


def capture_target_metadata_isolated(area,exclude_pid=None,timeout=8):
    x,y,w,h=map(int,area)
    command=helper_command('target','--area',str(x),str(y),str(w),str(h),
                           '--exclude-pid',str(int(exclude_pid or os.getpid())))
    return _run(command,timeout)


def capture_target_isolated(area,exclude_pid=None,timeout=8):
    metadata=capture_target_metadata_isolated(area,exclude_pid,timeout)
    return metadata['handle'],metadata['rect']


def probe_handle_isolated(handle,timeout=8):
    command=helper_command('target','--handle',str(int(handle)))
    return _run(command,timeout)
