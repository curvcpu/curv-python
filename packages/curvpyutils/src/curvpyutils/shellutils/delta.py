import subprocess
import sys
import os
from pathlib import Path
import difflib

from .which import Which


def print_delta(
    file_path1: str | Path,
    file_path2: str | Path,
    on_delta_missing: Which.OnMissingAction = Which.OnMissingAction.WARNING_AND_RAISE,
) -> None:
    """Invoke ``delta`` to diff two files if the binary is available; otherwise fall back.

    Behavior when ``delta`` is missing:
    - Prefer system ``diff -y`` if available
    - Otherwise, print a unified diff via ``difflib.unified_diff``

    Args:
        file_path1 (str|Path): the path to the first file to diff.
        file_path2 (str|Path): the path to the second file to diff.
        on_delta_missing (Which.OnMissingAction): how to handle missing ``delta`` (default: warning + raise; caught here to fall back)

    Raises:
        FileNotFoundError: if either of the file paths do not exist.
    """
    if not Path(file_path1).exists() or not Path(file_path2).exists():
        raise FileNotFoundError(f"File not found: {file_path1} or {file_path2}")

    original_exc: FileNotFoundError | None = None
    delta = None
    try:
        delta = Which("delta", on_missing_action=on_delta_missing)()
    except FileNotFoundError as e:
        # never fail fatally here; fall back to difflib
        original_exc = e
        delta = None

    if delta is not None:
        subprocess.run([delta, str(file_path1), str(file_path2)], check=False, stdout=sys.stdout, stderr=sys.stderr)
        return

    # Fallback 1: system diff -y if available
    diff = Which("diff", on_missing_action=Which.OnMissingAction.QUIET)()
    if diff is not None:
        subprocess.run([diff, "-y", str(file_path1), str(file_path2)], check=False, stdout=sys.stdout, stderr=sys.stderr)
        return

    # Fallback 2: Python difflib unified diff
    try:
        with open(file_path1, "r", encoding="utf-8", errors="replace") as f1, open(
            file_path2, "r", encoding="utf-8", errors="replace"
        ) as f2:
            a_lines = f1.readlines()
            b_lines = f2.readlines()
        for line in difflib.unified_diff(a_lines, b_lines, fromfile=str(file_path1), tofile=str(file_path2)):
            sys.stdout.write(line)
    except Exception:
        # If even the fallback fails for any unexpected reason, re-raise the original exception if we have it
        if original_exc is not None:
            raise original_exc
        raise

