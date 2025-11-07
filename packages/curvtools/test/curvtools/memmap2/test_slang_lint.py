"""Unit tests using slang to lint the memmap2's output SV file"""

import os
import tempfile
from pathlib import Path
import subprocess

import pytest
import sys

pytestmark = [pytest.mark.e2e, pytest.mark.tool_required("slang")]

from curvpyutils.shellutils import Which

class TestWhichSlang:
    """
    Test that slang binary is found and can be used to lint the memmap2's output SV file
    """
    def test_slang_in_path(self):
        which = Which("slang", on_missing_action=Which.OnMissingAction.ERROR_AND_RAISE)
        slang_path = which()
        assert slang_path is not None
        assert os.path.exists(slang_path)

class TestSlangLint:
    """
    Run slang on memmap2's output SV file and check that it passes
    """
    @classmethod
    def setup_class(cls):
        test_dir = Path(__file__).parent
        cls.sv_file_expected_with_inside = test_dir / "test_vectors" / "expected" / "expected_memmappkg_with_inside.sv"
        cls.sv_file_expected_without_inside = test_dir / "test_vectors" / "expected" / "expected_memmappkg_without_inside.sv"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sv', delete=False) as tmp_file:
            cls.slang_top_file = Path(tmp_file.name)
        cls.toml_file = test_dir / "test_vectors" / "input" / "example" / "memory_map.toml"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sv', delete=False) as tmp_file:
            cls.sv_file_generated = tmp_file.name
        
        # generate the slang_top.sv file
        cls._prepare_slang_top_file()

    @classmethod
    def _prepare_slang_top_file(cls):
        """Generate the slang_top.sv file"""
        test_dir = Path(__file__).parent

        # generate the slang_top.sv file into a temp path
        cmd = [
            sys.executable, "-m", "curvtools.cli.memmap2",
            "--config", str(cls.toml_file),
            "--generate-static-asserts", str(cls.slang_top_file)
        ]

        repo_root = Path(__file__).resolve().parents[5]
        env = dict(os.environ)
        env["PYTHONPATH"] = ":".join([
            str(repo_root / "packages" / "curvtools" / "src"),
            str(repo_root / "packages" / "curvpyutils" / "src"),
            str(repo_root / "packages" / "curv" / "src"),
            env.get("PYTHONPATH", "")
        ])
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(test_dir), env=env)

        # Check that the command succeeded
        assert result.returncode == 0, f"Command failed: {result.stderr}"
    
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

    def test_slang_lint_pass_expected_file(self):
        slang_bin = Which("slang", on_missing_action=Which.OnMissingAction.ERROR_AND_RAISE)
        for use_inside in [True, False]:
            # generate the generated file
            self._generate_sv_pkg_file(use_inside)

            # Lint the generated file
            result = subprocess.run([slang_bin(), 
                    "-DSLANG", 
                    "-DSIMULATION",
                    "-Wno-missing-top", 
                    str(self.slang_top_file),
                    str(self.sv_file_generated)
                ], capture_output=True, text=True, check=True)
            assert result.returncode == 0, f"Slang linting failed for {self.sv_file_generated} with use_inside={use_inside}: {result.stderr}"

    def test_slang_lint_pass_generated_file(self):
        """
        Lint the generated file with and without the inside range condition
        """
        slang_bin = Which("slang", on_missing_action=Which.OnMissingAction.ERROR_AND_RAISE)
        for use_inside in [True, False]:
            # generate the generated file
            self._generate_sv_pkg_file(use_inside)

            # Lint the generated file
            result = subprocess.run([slang_bin(), 
                    "-DSLANG", 
                    "-DSIMULATION",
                    "-Wno-missing-top", 
                    str(self.slang_top_file),
                    str(self.sv_file_generated)
                ], capture_output=True, text=True, check=True)
            assert result.returncode == 0, f"Slang linting failed for {self.sv_file_generated} with use_inside={use_inside}: {result.stderr}"

