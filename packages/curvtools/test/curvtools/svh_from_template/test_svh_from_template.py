#!/usr/bin/env python3
"""
Integration tests for curv-svh-from-template tool
"""
import subprocess
import tempfile
import os
import sys
import shutil
from pathlib import Path
from curvpyutils import test_helpers
import pytest

pytestmark = [pytest.mark.e2e]

def _make_svh_from_template_cmd() -> list[str]:
    """
    Prefer installed binary; fallback to module execution.
    """
    if shutil.which("curv-svh-from-template"):
        return ["curv-svh-from-template"]
    return [sys.executable, "-m", "curvtools.cli.svh_from_template.svh_from_template"]

def _get_py_env_with_workspace() -> dict:
    """
    Get environment with PYTHONPATH set for local package imports.
    """
    repo_root = Path(__file__).resolve().parents[5]
    env = dict(os.environ)
    py_path = [
        str(repo_root / "packages" / "curvtools" / "src"),
        str(repo_root / "packages" / "curvpyutils" / "src"),
        str(repo_root / "packages" / "curv" / "src"),
    ]
    env["PYTHONPATH"] = ":".join(py_path + [env.get("PYTHONPATH", "")])
    return env

class TestIntegration:
    """Integration tests for curv-svh-from-template"""
    @classmethod
    def setup_class(cls):
        cls.here = Path(__file__).parent
        cls.expected_test1 = cls.here / "test_vectors" / "expected" / "flashdefines.svh"
        cls.expected_multi = cls.here / "test_vectors" / "expected" / "multi_var_template.svh"
    
    def test_svh_from_template(self, tmp_path: Path):
        """Test that curv-svh-from-template generates correct output"""

        tmp_output = tmp_path / "flashdefines.svh"

        # Run curv-svh-from-template
        cmd = _make_svh_from_template_cmd() + [
            "--template-file", str(self.here / "test_vectors" / "input" / "flashdefines.svh.tmpl"),
            "--output-file", str(tmp_output),
            "--var", "RAMS_DIR=/a/b/c",
        ]

        env = _get_py_env_with_workspace() if not shutil.which("curv-svh-from-template") else None
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)

        # Check that curv-svh-from-template passed
        assert result.returncode == 0, f"curv-svh-from-template should have passed, but got:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        assert test_helpers.compare_files(
            str(tmp_output),
            str(self.expected_test1),
            verbose=True,
            show_delta=True,
        ), f"{Path(self.expected_test1).name} output does not match expected output"

    def test_svh_from_template_with_multiple_vars(self, tmp_path: Path):
        """Ensure multiple variables are substituted correctly"""

        tmp_output = tmp_path / "multi_var_template.svh"

        cmd = _make_svh_from_template_cmd() + [
            "--template-file",
            str(self.here / "test_vectors" / "input" / "multi_var_template.svh.tmpl"),
            "--output-file",
            str(tmp_output),
            "--var",
            "PRIMARY_DIR=/primary/path",
            "--var",
            "SECONDARY_DIR=/secondary/path",
        ]

        env = _get_py_env_with_workspace() if not shutil.which("curv-svh-from-template") else None
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)

        assert (
            result.returncode == 0
        ), f"curv-svh-from-template should have passed, but got:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        assert test_helpers.compare_files(
            str(tmp_output),
            str(self.expected_multi),
            verbose=True,
            show_delta=True,
        ), f"{Path(self.expected_multi).name} output does not match expected output"

