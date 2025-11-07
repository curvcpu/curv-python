#!/usr/bin/env python3
"""
Test that verifies the Jinja2 template population works without crashing.
"""
import subprocess
import sys
import os
from pathlib import Path
import pytest
pytestmark = [pytest.mark.e2e]

def test_populate_jinja_template():
    """Test that memmap2.py can populate the default Jinja2 template without crashing."""

    # Get the paths
    test_dir = Path(__file__).parent
    toml_file = test_dir / "test_vectors" / "input" / "example" / "memory_map.toml"
    output_file = test_dir / "test_output.sv"

    # Ensure TOML file exists
    assert toml_file.exists(), f"TOML file not found: {toml_file}"

    # Build the command (no --input_template to use default template)
    cmd = [
        sys.executable,
        "-m",
        "curvtools.cli.memmap2",
        "--config", str(toml_file),
        "--output", str(output_file)
    ]

    try:
        # Run the command
        repo_root = Path(__file__).resolve().parents[5]
        env = dict(os.environ)
        env["PYTHONPATH"] = ":".join([
            str(repo_root / "packages" / "curvtools" / "src"),
            str(repo_root / "packages" / "curvpyutils" / "src"),
            str(repo_root / "packages" / "curv" / "src"),
            env.get("PYTHONPATH", "")
        ])
        result = subprocess.run(
            cmd,
            cwd=str(test_dir),
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        # Check that it succeeded (exit code 0)
        assert result.returncode == 0, f"Command failed with exit code {result.returncode}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"

        # Check that output file was created
        assert output_file.exists(), f"Output file was not created: {output_file}"

        # Check that output file has content
        content = output_file.read_text()
        assert len(content) > 0, "Output file is empty"

        # Basic checks that the output looks like SystemVerilog
        assert "package memmappkg;" in content, "Output doesn't contain package declaration"
        assert "endpackage" in content, "Output doesn't contain endpackage"

    finally:
        # Clean up
        if output_file.exists():
            output_file.unlink()
