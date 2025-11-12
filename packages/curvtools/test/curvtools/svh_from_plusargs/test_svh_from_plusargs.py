#!/usr/bin/env python3
"""
Integration tests for curv-svh-from-plusargs tool
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


def _make_svh_from_plusargs_cmd() -> list[str]:
    """
    Prefer installed binary; fallback to module execution.
    """
    if shutil.which("curv-svh-from-plusargs"):
        return ["curv-svh-from-plusargs"]
    return [sys.executable, "-m", "curvtools.cli.svh_from_plusargs.svh_from_plusargs"]


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
    """Integration tests for curv-svh-from-plusargs tool"""
    @classmethod
    def setup_class(cls):
        cls.here = Path(__file__).parent
        cls.expected_test1 = cls.here / "expected" / "generated-by-curv-svh-from-plusargs.svh"
    
    def test_svh_from_plusargs(self, tmp_path: Path):
        """Test that curv-svh-from-plusargs passes"""

        # Use the same filename as expected output so include guard matches
        tmp_output = tmp_path / "generated-by-curv-svh-from-plusargs.svh"

        # Run curv-svh-from-plusargs
        cmd = _make_svh_from_plusargs_cmd() + [
            "-o", str(tmp_output),
            "+TB_COMMON_ARG=\"testbench_version_of_val\"",
            "+SYN_COMMON_ARG=synthesis_version_of_val",
            "+TB_SHOULD_BE_BLANK_IN_SYNTHESIS=\"testbench_only_val\"",
            "+SYN_SHOULD_BE_BLANK_IN_SIMULATION=\"synthesis_only_val\"",
            "+TBONLY_SHOULD_BE_OMITTED_IN_SYNTHESIS=\"testbench_only_val2__omitted_in_synthesis\"",
            "+SYNONLY_SHOULD_BE_OMITTED_IN_SIMULATION=\"synthesis_only_val2__omitted_in_simulation\"",
            "+WILL_BE_IGNORED=123",
            "+BOTH_XXX=\"both_val\"",
        ]

        # Use workspace environment only for module execution (not for installed binaries)
        env = _get_py_env_with_workspace() if not shutil.which("curv-svh-from-plusargs") else None
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)

        # Check that curv-svh-from-plusargs passed
        assert result.returncode == 0, f"curv-svh-from-plusargs should have passed, but got:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        assert test_helpers.compare_files(
            str(tmp_output),
            str(self.expected_test1),
            verbose=True,
            show_delta=True,
        ), f"{Path(self.expected_test1).name} output does not match expected output"
