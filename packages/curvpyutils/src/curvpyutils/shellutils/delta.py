import subprocess
import sys

from . import Which


def print_delta(file_path1: str, file_path2: str) -> None:
    """Invoke ``delta`` to diff two files if the binary is available."""

    delta = Which("delta", on_missing_action=Which.OnMissingAction.ERROR_AND_RAISE)
    delta_bin = delta()
    if delta_bin is not None:
        subprocess.run([delta_bin, file_path1, file_path2], check=False, stdout=sys.stdout, stderr=sys.stderr)

