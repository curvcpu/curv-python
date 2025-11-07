import filecmp
from pathlib import Path
from rich.console import Console
from rich.text import Text
from curvpyutils.shellutils import print_delta, Which

def compare_files(test_file: str|Path, expected_file: str|Path, verbose: bool = False, show_delta: bool = False) -> bool:
    """
    Compares two files and returns True if they are the same, False otherwise.

    Args:
        test_file (str): the path to the test file to compare.
        expected_file (str): the path to the expected file to compare against.
        verbose (bool): if True, prints a message if the files are different.
        show_delta (bool): if True, shows the delta between the files if the files are different.

    Returns:
        bool: True if the files are the same, False otherwise.
    """
    cmp_result = filecmp.cmp(test_file, expected_file, shallow=False)
    if not cmp_result:
        if verbose:
            console = Console()
            console.print("MISMATCH: test file `", Text(str(test_file), "yellow"), "` <-> expected file `", Text(str(expected_file), "yellow"), "`")
        if show_delta:
            print_delta(test_file, expected_file, on_delta_missing=Which.OnMissingAction.WARNING)
    return cmp_result

__all__ = [
    "compare_files",
]