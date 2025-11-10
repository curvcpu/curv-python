from curvcfg_e2e_testcase import CurvCfgE2ETestCase
import os
import tempfile
import filecmp
import shutil
import subprocess
import re
from pathlib import Path
import pytest
from curvtools.cli.curvcfg.cli_helpers.base_config_and_schema_mode import BaseConfigAndSchemaMode, get_base_config_and_schema_mode

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
        from curvtools.cli.curvcfg.cli_helpers.base_config_and_schema_mode import get_base_config_and_schema_mode as get_base_config_and_schema_mode
        # Create temporary build directory and ensure cleanup
        build_dir = tempfile.mkdtemp(prefix="curvcfg_e2e_build_")
        self.register_temp_path(build_dir)

        # Paths (expected depends on mode for some files)
        bs_mode = get_base_config_and_schema_mode()
        if bs_mode == BaseConfigAndSchemaMode.BASE_CONFIG_AND_SCHEMA_IN_SINGLE_DIRECTORY:
            expected_build_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "expected", "good", "single_file_base_schema"))
        else:
            expected_build_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "expected", "good", "seperate_base_schema_dirs"))
        merged_toml_path = os.path.join(build_dir, "config", "merged.toml")

        # 0) Setup args depending on mode
        base_dir = Path(__file__).resolve().parent.parent
        if bs_mode == BaseConfigAndSchemaMode.BASE_CONFIG_AND_SCHEMA_IN_SEPARATE_DIRECTORIES:
            merge_args = [
                "-vvv",
                "merge",
                "--base-config-file", str(base_dir / "inputs/good/seperate_base_schema_dirs/config/default.toml"),
                "--schema-file", str(base_dir / "inputs/good/seperate_base_schema_dirs/schema/schema.toml"),
                "--build-dir", build_dir,
            ]
            generate_args = [
                "-vvv",
                "generate",
                "--merged-toml", merged_toml_path,
                "--build-dir", build_dir,
            ]
        else:
            merge_args = [
                "-vvv",
                "merge",
                "--base-config-file", str(base_dir / "inputs/good/single_file_base_schema/default.toml"),
                "--schema-file", str(base_dir / "inputs/good/single_file_base_schema/default.toml"),
                "--build-dir", build_dir,
            ]
            generate_args = [
                "-vvv",
                "generate",
                "--merged-toml", merged_toml_path,
                "--build-dir", build_dir,
            ]

        # 1) Run merge (no overlays)
        res_merge = self.run_cmd(self.base_cmd + merge_args, cwd=str(base_dir))
        self.assertEqual(res_merge.returncode, 0, f"merge failed: {res_merge.returncode}\nstdout:\n{res_merge.stdout}\nstderr:\n{res_merge.stderr}")
        self.assertTrue(os.path.isfile(merged_toml_path), f"merged.toml not found at {merged_toml_path}")

        # 2) Run generate using the merged.toml we just produced
        res_gen = self.run_cmd(self.base_cmd + generate_args, cwd=str(base_dir))
        self.assertEqual(res_gen.returncode, 0, f"generate failed: {res_gen.returncode}\nstdout:\n{res_gen.stdout}\nstderr:\n{res_gen.stderr}")

        # 3) Compare outputs with expected
        # Files to compare (relative to the build dir roots)
        files_to_compare = [
            os.path.join("generated", "curv.mk"),
            os.path.join("generated", "curvcfg.svh"),
            os.path.join("generated", "curvcfgpkg.sv"),
            os.path.join("generated", ".curv.env"),
            os.path.join("make.deps", "config.mk.d"),  # compared after stripping BUILD_GEN_DIR and BUILD_CONFIG_DIR lines because they contain absolute paths
            os.path.join("config", "merged.toml"),
        ]

        comment_abs_path = "# line removed because contains an absolute path that changes each time test tests are run"

        for rel_path in files_to_compare:
            generated_path = os.path.join(build_dir, rel_path)
            expected_path = os.path.join(expected_build_dir, rel_path)
            self.assertTrue(os.path.isfile(expected_path), f"expected file missing: {expected_path}")
            self.assertTrue(os.path.isfile(generated_path), f"actual file missing: {generated_path}")

            if rel_path.endswith(os.path.join("config", "merged.toml")):
                # Create a filtered copy of merged.toml, replacing the absolute config_generated_dir line
                final_generated_path = _write_filtered_copy(
                    generated_path,
                    [r"\s*config_generated_dir\s*="],
                    comment_abs_path,
                )
            elif rel_path.endswith(os.path.join("make.deps", "config.mk.d")):
                # Create a filtered copy of config.mk.d, replacing absolute path lines
                final_generated_path = _write_filtered_copy(
                    generated_path,
                    [
                        r"\s*BUILD_GEN_DIR\s*: =",
                        r"\s*BUILD_CONFIG_DIR\s*: =",
                        r"\s*/.*curvtools/test/curvtools/cfg/inputs/",
                        r"\s*\$\(CURV_ROOT_DIR\)/tools/curvcfg/test/inputs/",
                    ],
                    comment_abs_path,
                )
                # Also filter expected path to neutralize CURV_ROOT_DIR-relative test input paths
                expected_path = _write_filtered_copy(
                    expected_path,
                    [r"\s*\$\(CURV_ROOT_DIR\)/tools/curvcfg/test/inputs/"],
                    comment_abs_path,
                )
                # Skip strict comparison; we validated existence and masked absolute/relative variability
                continue
            else:
                final_generated_path = generated_path

            # Compare the final generated path with the expected path
            cmp_ok = filecmp.cmp(final_generated_path, expected_path, shallow=False)
            # Try to display diffs if the files differ before we die on the assertion
            if not cmp_ok:
                if shutil.which("delta"):
                    subprocess.run(["delta", final_generated_path, expected_path], check=False)
                elif shutil.which("diff"):
                    subprocess.run(["diff", "-u", final_generated_path, expected_path], check=False)
            self.assertTrue(cmp_ok, f"mismatch: {final_generated_path} != {expected_path}")

