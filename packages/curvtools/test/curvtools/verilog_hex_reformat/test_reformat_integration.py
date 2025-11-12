#!/usr/bin/env python3
"""
Integration tests for curv-verilog-hex-reformat tool
"""
import subprocess
import sys
import shutil
from pathlib import Path
from curvpyutils import test_helpers
import pytest

pytestmark = [pytest.mark.e2e]


def _make_verilog_hex_reformat_cmd() -> list[str]:
    """
    Prefer installed binary; fallback to module execution.
    """
    if shutil.which("curv-verilog-hex-reformat"):
        return ["curv-verilog-hex-reformat"]
    return [sys.executable, "-m", "curvtools.cli.verilog_hex_reformat.verilog_hex_reformat"]


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


def test_file1(tmp_path: Path):
    """Test that file1.vhex passes"""
    here = Path(__file__).parent
    input_file1 = here / "test_vectors" / "input" / "file1.vhex"
    expected_file1 = here / "test_vectors" / "expected" / "file1.vhex"
    tmp_output = tmp_path / "output.hex"

    # Run file1.vhex
    cmd = _make_verilog_hex_reformat_cmd() + [
        "-o", str(tmp_output),
        "--words-per-line", "1",
        "--addr-step", "0",
        str(input_file1)
    ]

    # Use workspace environment only for module execution (not for installed binaries)
    env = _get_py_env_with_workspace() if not shutil.which("curv-verilog-hex-reformat") else None
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    # Check that file1.vhex passed
    assert result.returncode == 0, "file1.hex should have passed"
    assert test_helpers.compare_files(
        str(tmp_output),
        str(expected_file1),
        verbose=True,
        show_delta=True), f"{expected_file1.name} output does not match expected output"

