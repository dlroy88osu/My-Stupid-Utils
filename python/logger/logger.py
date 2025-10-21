import atexit
import json
import os
import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# =============================================================================
# [ Globals ]
# =============================================================================
COLORS = {
    'TRACE': '\033[96m',
    'CYAN': '\033[96m',
    'DEBUG': '\033[94m',
    'BLUE': '\033[94m',
    'INFO': '\033[92m',
    'GREEN': '\033[92m',
    'WARN': '\033[93m',
    'YELLOW': '\033[93m',
    'ERROR': '\033[91m',
    'FATAL': '\033[91m',
    'RED': '\033[91m',
    'LOCATION': '\033[30m',
    'GRAY': '\033[30m',
    'RESET': '\033[0m',
}

START = time.time()

if os.path.exists('.env'):
    for line in Path('.env').read_text().splitlines():
        if line.startswith('#') or not line.strip():
            continue
        else:
            k, v = line.split('=')
            os.environ[k] = v

LEVELS = {'trace': 0, 'debug': 1, 'info': 2, 'warn': 3}
LOG_LEVEL = LEVELS[os.environ.get('LOG_LEVEL', 'info')]
LOG_DIR = os.environ.get('LOG_PATH') or os.getcwd()
LOG_PATH = os.path.join(LOG_DIR, 'logs.jsonl')
LOG_LEN = int(os.environ.get('LOG_LEN', 10_000))
VERBOSE = os.environ.get('VERBOSE', 'false') == 'true'

WRITER_QUEUE = queue.Queue(maxsize=500)
LISTENER_THREAD: Optional[threading.Thread] = None


# =============================================================================
# [ Threaded Queue Author ]
# =============================================================================
def vprint(message: str) -> None:
    print(f'=> {message}') if VERBOSE else None


def queue_listener_thread() -> None:
    vprint('Logger: Running')
    while True:
        item: Optional[Any] = WRITER_QUEUE.get()

        if item is None:
            vprint('Logger: Stopping')
            WRITER_QUEUE.task_done()
            break

        try:
            with open(LOG_PATH, 'a') as f:
                f.write(item + '\n')
        except IOError as e:
            vprint(f'Logger: Error writing to log file: {e}')
        finally:
            WRITER_QUEUE.task_done()
    vprint('Logger: Stopped')


LISTENER_THREAD = threading.Thread(target=queue_listener_thread, daemon=True)
LISTENER_THREAD.start()


def exit_log() -> None:
    WRITER_QUEUE.put(None)
    if LISTENER_THREAD:
        LISTENER_THREAD.join()

    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, 'r') as f:
            lines = f.readlines()
        if len(lines) > LOG_LEN:
            with open(LOG_PATH, 'w') as f:
                f.writelines(lines[-LOG_LEN:])


atexit.register(exit_log)


# =============================================================================
# [ Logging Functions ]
# =============================================================================
def sep(
    char: str = '-',
    color: Optional[str] = None,
    new_line_before: bool = False,
    new_line_after: bool = False,
    is_emoji: bool = False
) -> None:
    '''
    print a separator that covers the width of the console

    Args:
        char (str): a single character to print as line => default = '-'
        color (str): must be in: [cyan, blue, green, yellow, red, grey]
        new_line_before (bool): adds a newline before the sep line
        new_line_after (bool): adds a newline after the sep line
    '''
    print() if new_line_before else None
    if color:
        char = f'{COLORS[color.upper()]}{char}{COLORS['RESET']}'
    try:
        if is_emoji:
            width = int(os.get_terminal_size().columns / 2)
        else:
            width = os.get_terminal_size().columns
        print(char * width)
    except OSError:
        print(char * 80)
    print() if new_line_after else None


def title(message: str, char: str = '+', is_emoji: bool = False) -> None:
    sep(char, 'blue', new_line_before=True, is_emoji=is_emoji)
    info(message.title())
    sep(char, 'blue', new_line_before=True, is_emoji=is_emoji)


def trace(message: str) -> None:
    if LOG_LEVEL == 0:
        _log('TRACE', message)


def debug(message: str) -> None:
    if LOG_LEVEL <= 1:
        _log('DEBUG', message)


def info(message: str) -> None:
    if LOG_LEVEL <= 2:
        _log(' INFO', message)


def warn(message: str) -> None:
    if LOG_LEVEL <= 3:
        _log(' WARN', message)


def error(message: str, err: Exception | None = None) -> None:
    msg = (
        f'{message}\n\t{err.__class__.__name__} '
        f'-> {' '.join(str(err).splitlines())}'
        if err else message
    )
    _log('ERROR', msg)


def panic(message: str, err: Exception) -> None:
    print()
    msg = (
        f'{message}\n\t{err.__class__.__name__} '
        f'-> {' '.join(str(err).splitlines())}'
        if err else message
    )
    _log('FATAL', msg + f'\n{COLORS['RED']}=> Fatal Exit!{COLORS['RESET']}')
    print()
    try:
        exit_log()
    finally:
        sys.exit(1)


# =============================================================================
# [ Private Functions ]
# =============================================================================
def _log(level: str, message: str) -> None:
    _time = time.time() - START
    run_time = f'{int(_time // 60):3d}:{int(_time % 60):02d}'
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    frame = sys._getframe(2)
    line = frame.f_lineno
    file = frame.f_code.co_filename
    func = frame.f_code.co_name
    pretty_loc = f'{COLORS['LOCATION']}=> {file}:{line}{COLORS['RESET']}'

    print(f'{COLORS[level.strip()]}[ {run_time} : {level} ] '
          f':> {COLORS['RESET']}{message} {pretty_loc}')

    if level == 'FATAL':
        message = message.replace(COLORS['RED'], '')
        message = message.replace(COLORS['RESET'], '')
        message = ''.join([x.strip() for x in message.splitlines()])

    WRITER_QUEUE.put(json.dumps({
        'level': level.strip(),
        'timestamp': timestamp,
        'run_time': run_time.strip(),
        'file': file.replace('\\', '/'),
        'func': func,
        'line_number': line,
        'message': message
    }))
