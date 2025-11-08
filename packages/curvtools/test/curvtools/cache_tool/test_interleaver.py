#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path
import filecmp
import pytest
from curvpyutils.shellutils import print_delta

pytestmark = [pytest.mark.unit]


def _repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[5]


def _py_env_with_workspace() -> dict:
    repo_root = _repo_root_from_here()
    env = dict(os.environ)
    env["PYTHONPATH"] = ":".join([
        str(repo_root / "packages" / "curvtools" / "src"),
        str(repo_root / "packages" / "curvpyutils" / "src"),
        str(repo_root / "packages" / "curv" / "src"),
        env.get("PYTHONPATH", ""),
    ])
    return env


def test_interleaver_generates_expected_bin(tmp_path: Path):
    here = Path(__file__).parent
    vectors_root = here / "test_vectors" / "interleaver"
    input_dir = vectors_root / "input"
    expected_dir = vectors_root / "expected"

    out_file = tmp_path / "interleaved.bin"

    cmd = [
        sys.executable, "-m", "curvtools.cli.cache_tool.tag_ram_way_interleaver",
        str(input_dir / "way0.hex"),
        str(input_dir / "way1.hex"),
        "-o", str(out_file),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, env=_py_env_with_workspace())
    assert result.returncode == 0, f"Interleaver failed: {result.stderr}"

    expected_file = expected_dir / "interleaved.bin"
    assert expected_file.exists() and out_file.exists()
    same = filecmp.cmp(str(expected_file), str(out_file), shallow=False)
    if not same:
        print_delta(str(expected_file), str(out_file))
    assert same, "interleaved.bin does not match expected output"


