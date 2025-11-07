from __future__ import annotations
import os
import json
import tempfile
import unittest
from pathlib import Path
import sys
from typing import Callable
from curvpyutils.toml_utils import MergedTomlDict  # type: ignore
from curvpyutils.file_utils import DirWalker

import pytest
pytestmark = [pytest.mark.unit]

def make_simple_match_overlay_tomls() -> Callable[[str], bool]:
    """
    Make a simpler matcher function that can be used to test find_overlay_tomls_abs_paths().

    Returns:
        A function that matches overlay TOML files per the specified arguments.  Matcher function returns True
        if the file name matches the specified pattern, and False otherwise.
    """
    # default name to look for overlay TOML files with
    DEFAULT_OVERLAY_TOML_NAME = "overlay.toml"
    DEFAULT_OVERLAY_CAN_BE_DOTTED_SUFFIX = True   # whether to also allow e.g., "prod.overlay.toml"

    def match_overlay_tomls(file_name: str) -> bool:
        return (file_name==DEFAULT_OVERLAY_TOML_NAME) or (DEFAULT_OVERLAY_CAN_BE_DOTTED_SUFFIX and file_name.endswith(f".{DEFAULT_OVERLAY_TOML_NAME}"))
    return match_overlay_tomls

def find_overlay_tomls_abs_paths(root_dir: str, sub_dir: str, f_match_overlay_tomls: Callable[[str], bool]) -> list[str]:
    """
    Find all overlay.toml files in the directory tree starting from `sub_dir` and
    up to `root_dir`.
    
    Args:
        root_dir: The root directory to stop searching in.
        sub_dir: The directory to start searching in.
        f_match_overlay_tomls: a function that takes a file name and returns True/False to indicate a match

    Returns:
        A list of overlay.toml file absolute paths.
    """

    dirwalker = DirWalker(root_dir, sub_dir, f_match_overlay_tomls)
    rel_paths_list: list[str] = dirwalker.get_matching_files()
    return [str((Path(sub_dir) / path).resolve()) for path in rel_paths_list]

class TestMergeTomls(unittest.TestCase):
    here = Path(__file__).parent
    inputs_dir = here.parent / "test" / "test_vectors"/ "input" / "merged_toml_tests" / "hierarchy_of_overlays"
    inputs_dir_subdir1 = inputs_dir / "subdir1"
    inputs_dir_deepest_subdir = inputs_dir / "subdir1" / "subdir2"
    config_path = inputs_dir / "base_config" / "default.toml"
    schema_path = inputs_dir / "base_config" / "schema.toml"

    expected_overlay_toml_files_abs_paths:list[Path] = [
        (inputs_dir / "subdir1" / "overlay.toml").resolve(),
        (inputs_dir_deepest_subdir / "overlay.toml").resolve(),
    ]

    def test_find_overlay_tomls(self):
        # get the overlay toml files
        overlay_toml_files = find_overlay_tomls_abs_paths(str(self.inputs_dir), str(self.inputs_dir_deepest_subdir), f_match_overlay_tomls=make_simple_match_overlay_tomls())

        self.assertEqual(len(overlay_toml_files), 2)
        self.assertEqual(overlay_toml_files[0], str(self.expected_overlay_toml_files_abs_paths[0]))
        self.assertEqual(overlay_toml_files[1], str(self.expected_overlay_toml_files_abs_paths[1]))

    def test_merged_toml_dict0(self):
        """
        Does not consider the subdirs, only the base config.
        """
        overlay_toml_files = find_overlay_tomls_abs_paths(str(self.inputs_dir), str(self.inputs_dir), f_match_overlay_tomls=make_simple_match_overlay_tomls())
        merged_toml_dict = MergedTomlDict.from_toml_files(str(self.config_path), overlay_toml_files)
        self.assertEqual(merged_toml_dict['cache']['sets'], 4)

    def test_merged_toml_dict1(self):
        """
        Goes only to the first subdir, subdir1.
        """
        overlay_toml_files = find_overlay_tomls_abs_paths(str(self.inputs_dir), str(self.inputs_dir_subdir1), f_match_overlay_tomls=make_simple_match_overlay_tomls())
        merged_toml_dict = MergedTomlDict.from_toml_files(str(self.config_path), overlay_toml_files)
        self.assertEqual(merged_toml_dict['cache']['sets'], 8)

    def test_merged_toml_dict2(self):
        """
        Goes all the way to the deepest subdir.
        """
        overlay_toml_files = find_overlay_tomls_abs_paths(str(self.inputs_dir), str(self.inputs_dir_deepest_subdir), f_match_overlay_tomls=make_simple_match_overlay_tomls())
        merged_toml_dict = MergedTomlDict.from_toml_files(str(self.config_path), overlay_toml_files)
        self.assertEqual(merged_toml_dict['cache']['sets'], 16)

    def test_write_to_file(self):
        """
        Writes the merged TOML dict to a file.
        """
        # get the overlay toml files
        overlay_toml_files = find_overlay_tomls_abs_paths(str(self.inputs_dir), str(self.inputs_dir_deepest_subdir), f_match_overlay_tomls=make_simple_match_overlay_tomls())

        merged_toml_dict = MergedTomlDict.from_toml_files(str(self.config_path), overlay_toml_files)
        with tempfile.TemporaryDirectory() as td:
            outdir = Path(td) / "generated"
            outdir.mkdir(parents=True, exist_ok=True)
            output_path = str(outdir / "merged.toml")
            merged_toml_dict.write_to_file(output_path)
            self.assertTrue(os.path.isfile(output_path))
            with open(output_path, "r") as f:
                toml_file_contents = f.read()

            # assert that these two lines appear in file, sequentially:
            #   [cache]
            #   sets = 16
            toml_file_lines = toml_file_contents.split("\n")
            assert_next_line = None
            for line in toml_file_lines:
                if assert_next_line is not None:
                    self.assertEqual(line, assert_next_line)
                    break
                if line == "[cache]":
                    assert_next_line = "sets = 16"

if __name__ == "__main__":
    unittest.main()
