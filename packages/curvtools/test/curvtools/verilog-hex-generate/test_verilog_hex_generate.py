#!/usr/bin/env python3
"""
Integration tests for curv-verilog-hex-generate tool
"""
import subprocess
import sys
import shutil
from pathlib import Path
from curvpyutils import test_helpers
import pytest

pytestmark = [pytest.mark.e2e]


def _make_verilog_hex_generate_cmd() -> list[str]:
    """
    Prefer installed binary; fallback to module execution.
    """
    if shutil.which("curv-verilog-hex-generate"):
        return ["curv-verilog-hex-generate"]
    return [sys.executable, "-m", "curvtools.cli.verilog_hex_generate.verilog_hex_generate"]


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


def test_repeated_01_x_16(tmp_path: Path):
    """Test that repeated_01_x_16 passes"""
    here = Path(__file__).parent
    expected_test1 = here / "expected" / "repeated_01_x_16.hex"
    tmp_output = tmp_path / "output.hex"

    # Run repeated_01_x_16
    cmd = _make_verilog_hex_generate_cmd() + [
        "-o", str(tmp_output),
        "-w", "16",
        "-t", "constant",
        "-C", "01"
    ]

    # Use workspace environment only for module execution (not for installed binaries)
    env = _get_py_env_with_workspace() if not shutil.which("curv-verilog-hex-generate") else None
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    # Check that repeated_01_x_16 passed
    assert result.returncode == 0, "repeated_01_x_16 should have passed"
    assert test_helpers.compare_files(
        str(tmp_output),
        str(expected_test1),
        verbose=True,
        show_delta=True), f"{expected_test1.name} output does not match expected output"


def test_repeated_fe_x_64(tmp_path: Path):
    """Test that repeated_fe_x_64 passes"""
    here = Path(__file__).parent
    expected_test2 = here / "expected" / "repeated_fe_x_64.hex"
    tmp_output = tmp_path / "output.hex"

    # Run repeated_fe_x_64
    cmd = _make_verilog_hex_generate_cmd() + [
        "-o", str(tmp_output),
        "-w", "64",
        "-t", "constant",
        "-C", "fe"
    ]

    # Use workspace environment only for module execution (not for installed binaries)
    env = _get_py_env_with_workspace() if not shutil.which("curv-verilog-hex-generate") else None
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    # Check that repeated_fe_x_64 passed
    assert result.returncode == 0, "repeated_fe_x_64 should have passed"
    assert test_helpers.compare_files(
        str(tmp_output),
        str(expected_test2),
        verbose=True,
        show_delta=True), f"{expected_test2.name} output does not match expected output"
