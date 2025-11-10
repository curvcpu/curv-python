import unittest
import os
import shutil
import tempfile
import json
import subprocess
import pytest
from curvpyutils.shellutils import print_delta
from curvpyutils.test_helpers import compare_files
import shutil
import sys
pytestmark = [pytest.mark.e2e]

class TestJson(unittest.TestCase):
    def setUp(self):
        self.test_files_dir = os.path.join(os.path.dirname(__file__), 'test_vectors')
    def make_json_file(self, json_output_file: str, first_input_file: str, second_input_file: str):
        arr = [
            {
                'path': first_input_file,
                'args': ['-f']
            },
            {
                'path': second_input_file,
                'args': ['-f']
            }
        ]
        with open(json_output_file, 'w') as f:
            json.dump(arr, f)
    def test_json(self):
        print(f"\n🧪 Running test_json...")

        # Create temp dir that will be cleaned up when test ends
        temp_dir = tempfile.mkdtemp()
        print(f"creating temp_dir: {temp_dir}")
        self.addCleanup(lambda: shutil.rmtree(temp_dir) if os.path.exists(temp_dir) else None)
        
        first_file_expected_output = os.path.join(self.test_files_dir, 'expected', 'contains_one_subst_block.sv')
        second_file_expected_output = os.path.join(self.test_files_dir, 'expected', 'contains_subst_at_start_and_end.sv')
        first_input_file = os.path.join(self.test_files_dir, 'input', 'contains_one_subst_block.sv')
        second_input_file = os.path.join(self.test_files_dir, 'input', 'contains_subst_at_start_and_end.sv')
        first_input_file_temp_copy_for_inplace_mod = os.path.join(temp_dir, 'contains_one_subst_block.sv')
        second_input_file_temp_copy_for_inplace_mod = os.path.join(temp_dir, 'contains_subst_at_start_and_end.sv')
        with open(first_input_file, 'r') as fsrc:
            with open(first_input_file_temp_copy_for_inplace_mod, 'w') as fdst:
                fdst.write(fsrc.read())
        with open(second_input_file, 'r') as fsrc:
            with open(second_input_file_temp_copy_for_inplace_mod, 'w') as fdst:
                fdst.write(fsrc.read())
        
        # with open(first_input_file_temp_copy_for_inplace_mod, 'r') as f:
        #     print(f"{ANSI_RED}first_input_file_contents_initial: {f.read()}{ANSI_RESET}")
        # with open(second_input_file_temp_copy_for_inplace_mod, 'r') as f:
        #     print(f"{ANSI_RED}second_input_file_contents_initial: {f.read()}{ANSI_RESET}")

        # Create temp json file path
        json_file = os.path.join(temp_dir, 'test.json')
        self.make_json_file(json_file, first_input_file=first_input_file_temp_copy_for_inplace_mod, second_input_file=second_input_file_temp_copy_for_inplace_mod)
        self.assertTrue(os.path.exists(json_file))
        with open(json_file, 'r') as f:
            json_data = json.load(f)
        # print(f"{ANSI_RED}json_data: {json_data}{ANSI_RESET}")
        item = json_data[0]
        self.assertEqual(item['path'], first_input_file_temp_copy_for_inplace_mod)
        self.assertEqual(item['args'], ['-f'])
        item = json_data[1]
        self.assertEqual(item['path'], second_input_file_temp_copy_for_inplace_mod)
        self.assertEqual(item['args'], ['-f'])
        # Prefer installed CLI; fallback to module execution
        base_cmd: list[str]
        if shutil.which("curv-subst"):
            base_cmd = ["curv-subst"]
        else:
            base_cmd = [sys.executable, "-m", "curvtools.cli.subst.subst"]
        cmd = base_cmd + ["-f", f"@json:{json_file}"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            # Fallback: if module execution failed due to missing curvtools import, try with PYTHONPATH
            if "No module named 'curvtools'" in (e.stderr or ""):
                env = os.environ.copy()
                try:
                    repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
                except Exception:
                    from pathlib import Path
                    repo_root = str(Path(__file__).resolve().parents[5])
                workspace_paths = [
                    os.path.join(repo_root, "packages", "curvtools", "src"),
                    os.path.join(repo_root, "packages", "curvpyutils", "src"),
                    os.path.join(repo_root, "packages", "curv", "src"),
                ]
                existing_pythonpath = env.get("PYTHONPATH", "")
                env["PYTHONPATH"] = os.pathsep.join([*workspace_paths, existing_pythonpath] if existing_pythonpath else workspace_paths)
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
            else:
                raise
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        self.assertTrue(os.path.exists(first_input_file))
        self.assertTrue(os.path.exists(second_input_file))
        cmp_result = compare_files(first_input_file_temp_copy_for_inplace_mod, first_file_expected_output)
        self.assertTrue(cmp_result)
        cmp_result = compare_files(second_input_file_temp_copy_for_inplace_mod, second_file_expected_output)
        self.assertTrue(cmp_result)
        print(f"✅ success on `{first_input_file}`")
        print(f"✅ success on `{second_input_file}`")
