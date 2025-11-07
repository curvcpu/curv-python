import subprocess
import sys
import os
from pathlib import Path

from .which import Which


def print_delta(file_path1: str|Path, file_path2: str|Path, on_delta_missing: Which.OnMissingAction = Which.OnMissingAction.WARNING) -> None:
    """Invoke ``delta`` to diff two files if the binary is available.

    Args:
        file_path1 (str|Path): the path to the first file to diff.
        file_path2 (str|Path): the path to the second file to diff.
        on_delta_missing (Which.OnMissingAction): the action to take if the delta binary is not available (default: warn)
    
    Raises:
        FileNotFoundError: if either of the file paths do not exist.
    """
    if not Path(file_path1).exists() or not Path(file_path2).exists():
        raise FileNotFoundError(f"File not found: {file_path1} or {file_path2}")

    delta = Which("delta", on_missing_action=on_delta_missing)()
    if delta is not None:
        subprocess.run([delta, str(file_path1), str(file_path2)], check=False, stdout=sys.stdout, stderr=sys.stderr)

