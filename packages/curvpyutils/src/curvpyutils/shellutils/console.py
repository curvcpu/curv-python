import os
import shutil
import sys


def _tty_width_height() -> tuple[int, int]:
    """Best-effort detection of terminal width and height."""

    for stream in (sys.stdout, sys.stderr, sys.stdin):
        try:
            if stream.isatty():
                size = os.get_terminal_size(stream.fileno())
                return size.columns, size.lines
        except (OSError, ValueError, AttributeError):
            continue

    try:
        import fcntl
        import struct
        import termios

        with open("/dev/tty") as tty:
            rows, cols, *_ = struct.unpack(
                "hhhh", fcntl.ioctl(tty, termios.TIOCGWINSZ, b"\0" * 8)
            )
            if cols:
                return cols, rows
    except Exception:  # noqa: BLE001 - best-effort detection
        pass

    fallback = shutil.get_terminal_size(fallback=(80, 24))
    return fallback.columns, fallback.lines


def get_console_width() -> int:
    return _tty_width_height()[0]


def get_console_height() -> int:
    return _tty_width_height()[1]

