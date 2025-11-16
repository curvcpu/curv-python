#!/usr/bin/env python3
"""
Integration tests for memmap2 tool
"""
import subprocess
import tempfile
import os
import filecmp
from pathlib import Path
from curvpyutils.shellutils import print_delta
from curvpyutils import test_helpers
import pytest
import sys
pytestmark = [pytest.mark.e2e]

class TestIntegration:
    """Integration tests for memmap2 tool"""
    @classmethod
    def setup_class(cls):
        cls.test_dir = Path(__file__).parent
        cls.toml_file = cls.test_dir / "test_vectors" / "input" / "example" / "memory_map.toml"
        cls.expected_file_first_41_lines = cls.test_dir / "test_vectors" / "expected" / "expetected_memmap_comment.txt"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sv', delete=False) as tmp_file:
            cls.tmp_output = tmp_file.name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp_file:
            cls.tmp_output_markdown = tmp_file.name
        cls.expected_file_with_inside = cls.test_dir / "test_vectors" / "expected" / "expected_memmappkg_with_inside.sv"
        cls.expected_file_without_inside = cls.test_dir / "test_vectors" / "expected" / "expected_memmappkg_without_inside.sv"
        cls.expected_file_markdown = cls.test_dir / "test_vectors" / "expected" / "expected_markdown.md"
    
    def _generate_sv_pkg_file(self, use_inside: bool = False):
        """Generate the SV package file"""
        cmd = [
            sys.executable,
            "-m",
            "curvtools.cli.memmap2",
            "--config", str(self.toml_file),
            "--output", self.tmp_output,
            "--use-inside" if use_inside else "--no-use-inside",
        ]
        repo_root = Path(__file__).resolve().parents[5]
        env = dict(os.environ)
        pfx = str(repo_root / "packages")
        py_path = [
            str(repo_root / "packages" / "curvtools" / "src"),
            str(repo_root / "packages" / "curvpyutils" / "src"),
            str(repo_root / "packages" / "curv" / "src"),
        ]
        env["PYTHONPATH"] = ":".join(py_path + [env.get("PYTHONPATH", "")])
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=str(self.test_dir), env=env)
        assert result.returncode == 0, f"Command failed: {result.stderr}"

    def _generate_markdown_file(self):
        """Generate the markdown file"""
        cmd = [
            sys.executable,
            "-m",
            "curvtools.cli.memmap2",
            "--config", str(self.toml_file),
            "--generate-docs", str(self.tmp_output_markdown)
        ]
        repo_root = Path(__file__).resolve().parents[5]
        env = dict(os.environ)
        pfx = str(repo_root / "packages")
        py_path = [
            str(repo_root / "packages" / "curvtools" / "src"),
            str(repo_root / "packages" / "curvpyutils" / "src"),
            str(repo_root / "packages" / "curv" / "src"),
        ]
        env["PYTHONPATH"] = ":".join(py_path + [env.get("PYTHONPATH", "")])
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=str(self.test_dir), env=env)
        assert result.returncode == 0, f"Command failed: {result.stderr}"

    def test_correct_pipe_alignment_and_centering_of_memmap_comment(self):
        """Test that the memmap comment is correctly aligned and centered"""
        toml_file = self.test_dir / "example_memory_map.toml"

        # Run the memmap2 tool
        self._generate_sv_pkg_file(use_inside=False)

        # remove all but the first 41 lines of the generated file
        with open(self.tmp_output, 'r') as f:
            lines = f.readlines()
        with open(self.tmp_output, 'w') as f:
            f.writelines(lines[:41])
            
        # Compare the generated file's first 41 lines with the expected file's first 41 lines
        assert test_helpers.compare_files(self.tmp_output, str(self.expected_file_first_41_lines), verbose=True, show_delta=True), \
            "Generated SV file's first 41 lines do not match expected output"

    @pytest.mark.parametrize("use_inside", [True, False])
    def test_sv_generation(self, use_inside: bool):
        """Test that SV generation produces expected output"""

        try:
            # generate the generated file
            self._generate_sv_pkg_file(use_inside)

            # Compare the generated file with expected
            assert test_helpers.compare_files(self.tmp_output, str(self.expected_file_with_inside if use_inside else self.expected_file_without_inside), verbose=True, show_delta=True), \
                "Generated SV file does not match expected output"

        finally:
            # Clean up temp file
            os.unlink(self.tmp_output)

    def test_markdown_generation(self):
        """Test that markdown generation produces expected output"""
        try:
            self._generate_markdown_file()
            assert test_helpers.compare_files(self.tmp_output_markdown, str(self.expected_file_markdown), verbose=True, show_delta=True), \
                "Generated markdown file does not match expected output"
        finally:
            os.unlink(self.tmp_output_markdown)

    def test_validation_passes(self):
        """Test that validation passes on the example TOML"""
        # Run validation
        cmd = [
            sys.executable, "-m", "curvtools.cli.memmap2",
            "--validate-only",
            "--config", str(self.toml_file)
        ]

        repo_root = Path(__file__).resolve().parents[5]
        env = dict(os.environ)
        env["PYTHONPATH"] = ":".join([
            str(repo_root / "packages" / "curvtools" / "src"),
            str(repo_root / "packages" / "curvpyutils" / "src"),
            str(repo_root / "packages" / "curv" / "src"),
            env.get("PYTHONPATH", "")
        ])
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.test_dir), env=env)

        # Check that validation passed
        assert result.returncode == 0, f"Validation failed: {result.stdout}\n{result.stderr}"
        assert "✓ Validation passed!" in result.stdout

    def test_validation_fails_on_invalid_toml(self):
        """Test that validation fails on invalid TOML"""

        # Create a temporary invalid TOML file
        invalid_toml = """
[slaves.test]
ranges = [
{ name = "Test", start = 0x00000000, end = 0x00000003, access = "invalid" }
]
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as tmp_file:
            tmp_file.write(invalid_toml)
            tmp_toml = tmp_file.name

        try:
            # Run validation on invalid TOML
            cmd = [
                sys.executable, "-m", "curvtools.cli.memmap2",
                "--validate-only",
                "--config", tmp_toml
            ]

            repo_root = Path(__file__).resolve().parents[5]
            env = dict(os.environ)
            env["PYTHONPATH"] = ":".join([
                str(repo_root / "packages" / "curvtools" / "src"),
                str(repo_root / "packages" / "curvpyutils" / "src"),
                str(repo_root / "packages" / "curv" / "src"),
                env.get("PYTHONPATH", "")
            ])
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.test_dir), env=env)

            # Check that validation failed
            assert result.returncode != 0, "Validation should have failed on invalid TOML"
            assert "ERROR" in result.stdout or "ERROR" in result.stderr

        finally:
            os.unlink(tmp_toml)
