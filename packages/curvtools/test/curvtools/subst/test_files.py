import unittest
import os
import sys
import shutil
import tempfile
import json
import subprocess
import pytest
from curvpyutils.shellutils import print_delta
from rich import get_console
from rich.text import Text
from curvpyutils.test_helpers import compare_files
from curvtools.cli.subst.replace import run_substitution_on_file

# optional list of test files to skip temporarily
SKIP_TEST_FILES = []

pytestmark = [pytest.mark.unit]

class TestFiles(unittest.TestCase):
    def setUp(self):
        self.test_files_input_dir = os.path.join(os.path.dirname(__file__), 'test_vectors', 'input')
        self.test_files_expected_dir = os.path.join(os.path.dirname(__file__), 'test_vectors', 'expected')
        self.remove_temp_dir = True
        #self.COLORS = get_colors(disable_colors=self.disable_colors)
        os.environ['SUBST_TEST_ENV_VAR'] = '42'
    def _is_expected_file_modified(self, test_file: str) -> bool:
        input_file = os.path.join(self.test_files_input_dir, os.path.basename(test_file))
        expected_file = os.path.join(self.test_files_expected_dir, os.path.basename(test_file))
        return not compare_files(input_file, expected_file)
    def _copy_all_test_files_to_temp_dir(self) -> str:
        temp_dir = tempfile.mkdtemp()
        for root, dirs, files in os.walk(self.test_files_input_dir):
            for file in files:
                # print(f"Copying file: {os.path.join(root, file)} to {os.path.join(temp_dir, file)}")
                shutil.copy(os.path.join(root, file), os.path.join(temp_dir, file))
        return temp_dir
    def _find_all_test_file_and_expected_pairs(self, test_file_temp_dir: str) -> dict[str,list[str]]:
        test_files_and_expected_pairs = {}
        for root, dirs, files in os.walk(test_file_temp_dir):
            for file in files:
                test_files_and_expected_pairs[file] = ((os.path.join(root, file), os.path.join(self.test_files_expected_dir, file)))
        return test_files_and_expected_pairs
    def test_files(self):
        files_processed = 0
        lambda_skip_fn = lambda x: any(x.endswith(y) for y in SKIP_TEST_FILES)
        try:
            temp_dir = self._copy_all_test_files_to_temp_dir()
            test_files_and_expected_pairs = self._find_all_test_file_and_expected_pairs(temp_dir)
            # print(f"test_files_and_expected_pairs: {test_files_and_expected_pairs}")
            for filename, (test_file, expected_file) in test_files_and_expected_pairs.items():
                print(f"Pair: {test_file} <-> {expected_file}")
                if lambda_skip_fn(test_file):
                    continue
                if test_file.endswith("extra-args.sv"):
                    extra_args = ["%s\n", "Hello, world!"]
                else:
                    extra_args = ""
                self.assertTrue(os.path.exists(test_file), f"test file `{test_file}` does not exist")
                self.assertTrue(os.path.exists(expected_file), f"expected file `{expected_file}` does not exist")
                print(f"🧪 Running test on file `{filename}`")
                file_modified = run_substitution_on_file(file_path=test_file, dry_run=False, verbose=True, force=True, extra_args=extra_args)
                self.assertEqual(file_modified, self._is_expected_file_modified(test_file), f"test file `{test_file}` was not modified after substitution")
                self.assertTrue(os.path.exists(test_file), f"test file `{test_file}` does not exist after substitution")
                self.assertTrue(os.path.exists(expected_file), f"expected file `{expected_file}` does not exist after substitution")
                cmp_result = compare_files(test_file, expected_file)
                if not cmp_result:
                    print(f"MISMATCH: test file `{test_file}` <-> expected file `{expected_file}`")
                    print_delta(test_file, expected_file)
                self.assertTrue(cmp_result, f"test file `{test_file}` does not match expected file `{expected_file}`")
                files_processed += 1
                #print(f"✅ success on {self.COLORS['GREEN']}`{filename}`{self.COLORS['RESET']}")
                get_console().print("✅ success on `", Text(filename, "green"), "`")
            # print(f"Files processed: {files_processed}")
            self.assertGreater(files_processed, 0, "⚠️ no files were processed")
        finally:
            if False:#self.remove_temp_dir:
                if os.path.exists(temp_dir):
                    if os.path.dirname(temp_dir).startswith('/tmp'):
                        #print(f"Removing temp directory: {temp_dir}")
                        get_console().print("Removing temp directory: ", Text(temp_dir, "yellow"))
                        shutil.rmtree(temp_dir)
                    else:
                        #print(f"Not removing temp directory: {temp_dir} because it's not under the /tmp directory as expected")
                        get_console().print("Not removing temp directory: ", Text(temp_dir, "yellow"), " because it's not under the /tmp directory as expected")
            else:
                #print(f"Not removing temp directory: {temp_dir} because self.remove_temp_dir is False")
                get_console().print("Not removing temp directory: ", Text(temp_dir, "yellow"), " because self.remove_temp_dir is False")

