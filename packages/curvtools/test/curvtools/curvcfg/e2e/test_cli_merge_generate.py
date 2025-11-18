from curvcfg_e2e_testcase import CurvCfgE2ETestCase
import os
import tempfile
import filecmp
import shutil
import subprocess
import re
from pathlib import Path
import pytest
from curvtools.cli.curvcfg.lib.globals.constants import (
    DEFAULT_MERGED_TOML_NAME, DEFAULT_MERGED_TOML_DIR, 
    DEFAULT_DEP_FILE_NAME, DEFAULT_DEP_FILE_DIR
)
from curvpyutils.test_helpers import compare_files
from curvpyutils.shellutils import print_delta, Which

pytestmark = pytest.mark.e2e

def _write_filtered_copy(src_path: str, regex_prefixes: list[str], replacement_comment: str) -> str:
    """
    Create a filtered copy of src_path where any line matching one of the
    provided regex_prefixes (anchored at line start; use ^ or leading spaces in
    the regex as needed) is replaced by replacement_comment.

    Returns the path to the filtered copy (src_path + ".cmp").
    """
    dst_path = src_path + ".cmp"
    compiled = [re.compile(p) for p in regex_prefixes]
    with open(src_path, "r", encoding="utf-8") as fin, open(dst_path, "w", encoding="utf-8") as fout:
        for line in fin:
            if any(rx.match(line) for rx in compiled):
                fout.write(replacement_comment + "\n")
            else:
                fout.write(line)
    return dst_path

class TestCliMergeGenerate(CurvCfgE2ETestCase):
    def test_cli_merge_generate(self) -> None:
        # Create temporary build directory and ensure cleanup
        build_dir = tempfile.mkdtemp(prefix="curvcfg_e2e_build_")
        self.register_temp_path(build_dir)

        # Paths (expected depends on mode for some files)
        expected_build_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "expected", "good", "seperate_base_schema_dirs"))
        merged_toml_path = os.path.join(build_dir, DEFAULT_MERGED_TOML_DIR, DEFAULT_MERGED_TOML_NAME)

        # 0) Setup args depending on mode
        base_dir = Path(__file__).resolve().parent.parent
        merge_args = [
            "-vvv",
            "merge",
            "--profile-file", str(base_dir / "inputs/good/seperate_base_schema_dirs/config/default.toml"),
            "--schema-file", str(base_dir / "inputs/good/seperate_base_schema_dirs/schema/schema.toml"),
            "--build-dir", build_dir,
        ]
        generate_args = [
            "-vvv",
            "generate",
            "--merged-file", merged_toml_path,
            "--build-dir", build_dir,
        ]

        # 1) Run merge (no overlays)
        res_merge = self.run_cmd(self.base_cmd + merge_args, cwd=str(base_dir))
        if res_merge.returncode != 0:
            self._force_keep_temps = True
        self.assertEqual(res_merge.returncode, 0, f"merge failed: {res_merge.returncode}\nstdout:\n{res_merge.stdout}\nstderr:\n{res_merge.stderr}")
        if res_merge.returncode != 0:
            self._force_keep_temps = True
        self.assertTrue(os.path.isfile(merged_toml_path), f"merged.toml not found at {merged_toml_path}")

        # 2) Run generate using the merged.toml we just produced
        res_gen = self.run_cmd(self.base_cmd + generate_args, cwd=str(base_dir))
        if res_gen.returncode != 0:
            self._force_keep_temps = True
        self.assertEqual(res_gen.returncode, 0, f"generate failed: {res_gen.returncode}\nstdout:\n{res_gen.stdout}\nstderr:\n{res_gen.stderr}")

        # 3) Compare outputs with expected
        # Files to compare (relative to the build dir roots)
        files_to_compare = [
            os.path.join("generated", "curv.mk"),
            os.path.join("generated", "curvcfg.svh"),
            os.path.join("generated", "curvcfgpkg.sv"),
            os.path.join("generated", ".curv.env"),
            os.path.join(DEFAULT_DEP_FILE_DIR, DEFAULT_DEP_FILE_NAME),  # compared after stripping BUILD_GEN_DIR and BUILD_CONFIG_DIR lines because they contain absolute paths
            os.path.join(DEFAULT_MERGED_TOML_DIR, DEFAULT_MERGED_TOML_NAME),
        ]

        comment_abs_path = "# line removed because contains an absolute path that changes each time test tests are run"

        for rel_path in files_to_compare:
            generated_path = os.path.join(build_dir, rel_path)
            expected_path = os.path.join(expected_build_dir, rel_path)
            self.assertTrue(os.path.isfile(expected_path), f"expected file missing: {expected_path}")
            self.assertTrue(os.path.isfile(generated_path), f"actual file missing: {generated_path}")

            if rel_path.endswith(os.path.join(DEFAULT_DEP_FILE_DIR, DEFAULT_DEP_FILE_NAME)):
                # Create a filtered copy of config.mk.d, replacing absolute path lines
                final_generated_path = _write_filtered_copy(
                    generated_path,
                    [
                        r"\s*BUILD_GEN_DIR\s*:=",
                        r"\s*BUILD_CONFIG_DIR\s*:=",
                        r"\s*/.*curvtools/test/curvtools/curvcfg/inputs/",
                        r"\s*\$\(CURV_ROOT_DIR\)/tools/curvcfg/test/inputs/",
                    ],
                    comment_abs_path,
                )
                # Also filter expected path to neutralize CURV_ROOT_DIR-relative test input paths
                expected_path_tmp = _write_filtered_copy(
                    expected_path,
                    [r"\s*\$\(CURV_ROOT_DIR\)/tools/curvcfg/test/inputs/"],
                    comment_abs_path,
                )
                self.register_temp_path(expected_path_tmp)
                self.register_temp_path(final_generated_path)
            else:
                final_generated_path = generated_path
                expected_path_tmp = expected_path

            # Compare the final generated path with the expected path
            cmp_ok = compare_files(final_generated_path, expected_path_tmp)
            # Try to display diffs if the files differ before we die on the assertion
            if not cmp_ok:
                self._force_keep_temps = True
                print_delta(final_generated_path, expected_path, on_delta_missing=Which.OnMissingAction.ERROR)
            self.assertTrue(cmp_ok, f"mismatch: {final_generated_path} != {expected_path}")

class TestMergeWithOverlayPathList(CurvCfgE2ETestCase):
    def test_cli_merge_with_overlay_path_list(self) -> None:
        # Create temporary build directory and ensure cleanup
        build_dir = tempfile.mkdtemp(prefix="curvcfg_e2e_build_")
        self.register_temp_path(build_dir)
        
    def test_cli_merge_generate(self) -> None:
        # Create temporary build directory and ensure cleanup
        build_dir = tempfile.mkdtemp(prefix="curvcfg_e2e_build_")
        self.register_temp_path(build_dir)

        # Paths
        expected_build_dir = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "expected", "several_overlay_tomls"))
        merged_toml_path = os.path.join(build_dir, DEFAULT_MERGED_TOML_DIR, DEFAULT_MERGED_TOML_NAME)

        # 0) Setup args
        base_dir = Path(__file__).resolve().parent.parent
        merge_args = [
            "-vvv",
            "merge",
            "--profile-file", str(base_dir / "inputs/several_overlay_tomls/profiles/base.toml"),
            "--schema-file", str(base_dir / "inputs/several_overlay_tomls/schema/schema.toml"),
            "--overlay-path", str(base_dir / "inputs/several_overlay_tomls/overlay1.toml"),
            "--overlay-path", str(base_dir / "inputs/several_overlay_tomls/overlay2.toml"),
            "--overlay-path", str(base_dir / "inputs/several_overlay_tomls/overlay3.toml"),
            "--build-dir", build_dir,
        ]

        # 1) Run merge
        res_merge = self.run_cmd(self.base_cmd + merge_args, cwd=str(base_dir))
        if res_merge.returncode != 0:
            self._force_keep_temps = True
        self.assertEqual(res_merge.returncode, 0, f"merge failed: {res_merge.returncode}\nstdout:\n{res_merge.stdout}\nstderr:\n{res_merge.stderr}")
        if res_merge.returncode != 0:
            self._force_keep_temps = True
        self.assertTrue(os.path.isfile(merged_toml_path), f"merged.toml not found at {merged_toml_path}")

        # 2) compare files
        files_to_compare = [
            os.path.join(DEFAULT_MERGED_TOML_DIR, DEFAULT_MERGED_TOML_NAME),
            os.path.join(DEFAULT_DEP_FILE_DIR, DEFAULT_DEP_FILE_NAME),
        ]
        for rel_path in files_to_compare:
            generated_path = os.path.join(build_dir, rel_path)
            comment_abs_path = "# line removed because contains an absolute path that changes each time test tests are run"
            final_generated_path = _write_filtered_copy(
                generated_path,
                [
                    r"\s*BUILD_GEN_DIR\s*:=",
                    r"\s*BUILD_CONFIG_DIR\s*:=",
                    r"\s*/.*curvtools/test/curvtools/curvcfg/inputs/",
                    r"\s*\$\(CURV_ROOT_DIR\)/tools/curvcfg/test/inputs/",
                ],
                comment_abs_path,
            )
            expected_path = os.path.join(expected_build_dir, rel_path)
            self.assertTrue(os.path.isfile(expected_path), f"expected file missing: {expected_path}")
            self.assertTrue(os.path.isfile(final_generated_path), f"actual file missing: {final_generated_path}")
            cmp_ok = compare_files(final_generated_path, expected_path)
            if not cmp_ok:
                self._force_keep_temps = True
                print_delta(final_generated_path, expected_path, on_delta_missing=Which.OnMissingAction.ERROR)
            self.assertTrue(cmp_ok, f"mismatch: {final_generated_path} != {expected_path}")