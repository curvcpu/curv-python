"""Unit tests using slang to lint the memmap2's output SV file"""

import os
import tempfile
from pathlib import Path
import subprocess

import pytest
import sys
pytestmark = [pytest.mark.e2e, pytest.mark.tool_required("verilator")]

from curvpyutils.shellutils import Which

class TestWhichVerilator:
    """
    Test that verilator binary is found and can be used to lint the memmap2's output SV file
    """
    def test_verilator_in_path(self):
        which = Which("verilator", on_missing_action=Which.OnMissingAction.ERROR_AND_RAISE)
        verilator_path = which()
        assert verilator_path is not None
        assert os.path.exists(verilator_path)

class TestVerilatorLint:
    """
    Run slang on memmap2's output SV file and check that it passes
    """
    @classmethod
    def setup_class(cls):
        test_dir = Path(__file__).parent
        cls.sv_file_expected_with_inside = test_dir / "test_vectors" / "expected" / "expected_memmappkg_with_inside.sv"
        cls.sv_file_expected_without_inside = test_dir / "test_vectors" / "expected" / "expected_memmappkg_without_inside.sv"
        cls.toml_file = test_dir / "test_vectors" / "input" / "example" / "memory_map.toml"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sv', delete=False) as tmp_file:
            cls.sv_file_generated = tmp_file.name

    def test_verilator_lint_pass_expected_file(self):
        """
        Verilator lint the expected files with and without the inside range condition just as a sanity check
        """
        verilator_bin = Which("verilator", on_missing_action=Which.OnMissingAction.ERROR_AND_RAISE)
        for sv_file_expected in [self.sv_file_expected_with_inside, self.sv_file_expected_without_inside]:
            result = subprocess.run([verilator_bin(), 
                "--lint-only", 
                "--sv", 
                "-Wall", 
                "-Wno-declfilename",
                str(sv_file_expected)
                ], capture_output=True, text=True, check=True)
            assert result.returncode == 0, f"Verilator linting failed for {sv_file_expected}: {result.stderr}"

    def _generate_sv_pkg_file(self, use_inside: bool = False):
        """Generate the SV package file"""
        test_dir = Path(__file__).parent
        cmd = [
            sys.executable,
            "-m",
            "curvtools.cli.memmap2",
            "--config", str(self.toml_file),
            "--output", self.sv_file_generated,
            "--use-inside" if use_inside else "--no-use-inside",
        ]
        repo_root = Path(__file__).resolve().parents[5]
        env = dict(os.environ)
        env["PYTHONPATH"] = ":".join([
            str(repo_root / "packages" / "curvtools" / "src"),
            str(repo_root / "packages" / "curvpyutils" / "src"),
            str(repo_root / "packages" / "curv" / "src"),
            env.get("PYTHONPATH", "")
        ])
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=str(test_dir), env=env)
        assert result.returncode == 0, f"Command failed: {result.stderr}"

    def test_slang_lint_pass_generated_file(self):
        """
        Verilator lint the generated file and check that it passes
        """

        for use_inside in [True, False]:
            # generate the generated file
            self._generate_sv_pkg_file(use_inside)

            # Lint the generated file
            verilator_bin = Which("verilator", on_missing_action=Which.OnMissingAction.ERROR_AND_RAISE)
            result = subprocess.run([verilator_bin(), 
                "--lint-only", 
                "--sv", 
                "-Wall", 
                "-Wno-declfilename", 
                str(self.sv_file_generated)
                ], capture_output=True, text=True, check=True)
            assert result.returncode == 0

