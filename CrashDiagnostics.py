"""Crash/fault logging that remains useful even for native ctypes failures."""
from __future__ import annotations

import faulthandler
import os
import platform
import sys
import threading
import time
import traceback
from pathlib import Path

from RuntimePaths import atomic_write_text, data_dir

_LOG_STREAM = None
_INSTALLED = False
_LOG_LOCK = threading.RLock()
_MAX_LOG_BYTES = 2 * 1024 * 1024

LOG_DIR = data_dir() / 'logs'
CRASH_LOG = LOG_DIR / 'DrawStudio-crash.log'
SESSION_LOG = LOG_DIR / 'DrawStudio-session.log'
RUN_MARKER = LOG_DIR / 'DrawStudio-running.marker'
PREVIOUS_RUN_UNCLEAN = False
RUN_MARKER_OWNED = False


def _stamp():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def _rotate_if_large(path: Path, limit: int = _MAX_LOG_BYTES) -> None:
    """Keep logs bounded so a long-running beta cannot fill the user profile."""
    try:
        if not path.exists() or path.stat().st_size <= limit:
            return
        backup = path.with_suffix(path.suffix + '.1')
        backup.unlink(missing_ok=True)
        os.replace(path, backup)
    except OSError:
        # Diagnostics must never become a reason the app cannot start.
        return


def log_event(message):
    try:
        with _LOG_LOCK:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            _rotate_if_large(SESSION_LOG)
            with SESSION_LOG.open('a', encoding='utf-8') as stream:
                stream.write(f'[{_stamp()}] {message}\n')
    except Exception:
        pass


def install():
    global _LOG_STREAM, _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        _rotate_if_large(CRASH_LOG)
        _rotate_if_large(SESSION_LOG)
        _LOG_STREAM = CRASH_LOG.open('a', encoding='utf-8', buffering=1)
        _LOG_STREAM.write('\n' + '=' * 72 + '\n')
        _LOG_STREAM.write(f'[{_stamp()}] Draw Studio start\n')
        _LOG_STREAM.write(f'Python: {sys.version.replace(chr(10), " ")}\n')
        _LOG_STREAM.write(f'Executable: {sys.executable}\n')
        _LOG_STREAM.write(f'Platform: {platform.platform()}\n')
        _LOG_STREAM.write(f'PID: {os.getpid()}\n')
        _LOG_STREAM.flush()
        faulthandler.enable(file=_LOG_STREAM, all_threads=True)
    except Exception:
        _LOG_STREAM = None

    previous_hook = sys.excepthook

    def exception_hook(exc_type, exc, tb):
        try:
            if _LOG_STREAM:
                _LOG_STREAM.write(f'[{_stamp()}] Unhandled exception\n')
                traceback.print_exception(exc_type, exc, tb, file=_LOG_STREAM)
                _LOG_STREAM.flush()
        except Exception:
            pass
        finally:
            try:
                previous_hook(exc_type, exc, tb)
            except Exception:
                pass

    sys.excepthook = exception_hook

    if hasattr(threading, 'excepthook'):
        previous_thread_hook = threading.excepthook

        def thread_hook(args):
            try:
                if _LOG_STREAM:
                    name = getattr(getattr(args, 'thread', None), 'name', '<unknown>')
                    _LOG_STREAM.write(f'[{_stamp()}] Unhandled thread exception: {name}\n')
                    traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback, file=_LOG_STREAM)
                    _LOG_STREAM.flush()
            except Exception:
                pass
            finally:
                try:
                    previous_thread_hook(args)
                except Exception:
                    pass

        threading.excepthook = thread_hook

    log_event('Crash diagnostics enabled.')


def begin_run_marker():
    """Claim the clean-shutdown marker after the single-instance lock is held."""
    global PREVIOUS_RUN_UNCLEAN, RUN_MARKER_OWNED
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        PREVIOUS_RUN_UNCLEAN = RUN_MARKER.exists()
        atomic_write_text(RUN_MARKER, f'pid={os.getpid()} started={_stamp()}\n')
        RUN_MARKER_OWNED = True
        log_event(f'Run marker claimed. previous_unclean={PREVIOUS_RUN_UNCLEAN}.')
    except OSError as error:
        RUN_MARKER_OWNED = False
        log_event(f'Run marker could not be created: {error}.')


def previous_run_unclean():
    return bool(PREVIOUS_RUN_UNCLEAN)


def clean_exit():
    global RUN_MARKER_OWNED
    try:
        if RUN_MARKER_OWNED:
            # Do not delete another process's marker if ownership changed.
            try:
                content = RUN_MARKER.read_text(encoding='utf-8')
            except OSError:
                content = ''
            if content.split() and content.split()[0] == f'pid={os.getpid()}':
                RUN_MARKER.unlink(missing_ok=True)
            RUN_MARKER_OWNED = False
        log_event('Clean shutdown recorded.')
    except Exception:
        pass
