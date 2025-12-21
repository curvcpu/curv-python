import filecmp
from pathlib import Path
from rich.console import Console
from rich.text import Text
from curvpyutils.shellutils import print_delta, Which
from curvpyutils.toml_utils import TomlCanonicalizer
from typing import Optional

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

def compare_toml_files(test_file: str|Path, expected_file: str|Path, verbose: bool = False, show_delta: bool = False, delete_temp_files: bool = True, debug_output_silent: bool = True) -> bool:
    """
    Compares temp copies of two canonicalized TOML files and returns True if they are the same, False otherwise.

    Args:
        test_file (str): the path to the test file to compare.
        expected_file (str): the path to the expected file to compare against.
        verbose (bool): if True, prints a message if the files are different.
        show_delta (bool): if True, shows the delta between the files if the files are different.
        delete_temp_files (bool): if True, deletes the temporary files after comparison.
        debug_output_silent (bool): if True, does not print certain debug output from the
        canonicalizatizer, which is not helpful unless that is what you are debugging. Defaults to True.
    Returns:
        bool: True if the files are the same, False otherwise.
    """
    try:
        test_temp_file = TomlCanonicalizer(test_file, silent=debug_output_silent).temp_file
        expected_temp_file = TomlCanonicalizer(expected_file, silent=debug_output_silent).temp_file
        return compare_files(test_temp_file, expected_temp_file, verbose=verbose, show_delta=show_delta)
    finally:
        if delete_temp_files:
            if test_temp_file is not None and test_temp_file.exists() and test_temp_file.is_file():
                test_temp_file.unlink()
            if expected_temp_file is not None and expected_temp_file.exists() and expected_temp_file.is_file():
                expected_temp_file.unlink()
        else:
            print(f"Keeping temp files: {test_temp_file} and {expected_temp_file}")

__all__ = [
    "compare_files",
    "compare_toml_files",
]