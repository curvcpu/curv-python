#!/usr/bin/env python3
"""
End-to-end validation tests for memmap2 tool using subprocess calls
"""
import subprocess
import pytest
from pathlib import Path
import sys
import os
pytestmark = [pytest.mark.e2e]


def test_invalid_no_flash_control_section():
    """Test that missing flash_control range is detected"""
    test_dir = Path(__file__).parent
    invalid_file = test_dir / "test_vectors" / "input" / "invalid_no_flash_control_section.toml"

    cmd = [
        sys.executable, "-m", "curvtools.cli.memmap2",
        "--validate-only",
        "--config", str(invalid_file)
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

    # Should fail validation
    assert result.returncode != 0, "Validation should fail for slave with registers but no ranges"
    assert "has registers/buffers but no ranges defined" in result.stdout


def test_invalid_regs_not_in_range():
    """Test that registers outside their range are detected"""
    test_dir = Path(__file__).parent
    invalid_file = test_dir / "test_vectors" / "input" / "invalid_regs_not_in_range.toml"

    cmd = [
        sys.executable, "-m", "curvtools.cli.memmap2",
        "--validate-only",
        "--config", str(invalid_file)
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

    # Should fail validation
    assert result.returncode != 0, "Validation should fail for registers outside range"
    assert "not contained in any" in result.stdout


def test_invalid_unnamed_range():
    """Test that unnamed ranges are rejected"""
    test_dir = Path(__file__).parent
    invalid_file = test_dir / "test_vectors" / "input" / "invalid_unnamed_range.toml"

    cmd = [
        sys.executable, "-m", "curvtools.cli.memmap2",
        "--validate-only",
        "--config", str(invalid_file)
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

    # Should fail validation
    assert result.returncode != 0, "Validation should fail for unnamed range"
    assert "Range names cannot be empty" in result.stdout

def test_registers_cannot_be_children_of_a_range_in_toml():
    """Test that registers cannot be children of a range in TOML"""
    test_dir = Path(__file__).parent
    toml_file = test_dir / "test_vectors" / "input" / "registers_cannot_be_children_of_a_range_in_toml.toml"
    cmd = [
        sys.executable, "-m", "curvtools.cli.memmap2",
        "--validate-only",
        "--config", str(toml_file)
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
    assert result.returncode != 0, "Validation should fail for registers cannot be children of a range in TOML"
    assert "registers and buffers must be direct children of a slave in TOML" in result.stdout

def test_buffers_cannot_be_children_of_a_range_in_toml():
    """Test that buffers cannot be children of a range in TOML"""
    test_dir = Path(__file__).parent
    toml_file = test_dir / "test_vectors" / "input" / "buffers_cannot_be_children_of_a_range_in_toml.toml"
    cmd = [
        sys.executable, "-m", "curvtools.cli.memmap2",
        "--validate-only",
        "--config", str(toml_file)
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
    assert result.returncode != 0, "Validation should fail for buffers cannot be children of a range in TOML"
    assert "registers and buffers must be direct children of a slave in TOML" in result.stdout


def test_registers_must_have_addr():
    """Test that registers must use addr (start is invalid)"""
    test_dir = Path(__file__).parent
    toml_file = test_dir / "test_vectors" / "input" / "registers_must_have_addr.toml"
    cmd = [
        sys.executable, "-m", "curvtools.cli.memmap2",
        "--validate-only",
        "--config", str(toml_file)
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
    assert result.returncode != 0, "Validation should fail when registers do not use addr"