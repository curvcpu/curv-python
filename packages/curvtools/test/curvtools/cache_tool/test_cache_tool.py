#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path
import filecmp
import pytest
from curvpyutils.shellutils import print_delta

pytestmark = [pytest.mark.unit]


def _compare_trees(expected_dir: Path, actual_dir: Path, verbose: bool = False) -> None:
    files_compared = 0
    for root, _dirs, files in os.walk(expected_dir):
        for f in files:
            expected_path = Path(root) / f
            rel = expected_path.relative_to(expected_dir)
            actual_path = actual_dir / rel
            assert actual_path.exists(), f"missing generated file: {actual_path}"
            same = filecmp.cmp(str(expected_path), str(actual_path), shallow=False)
            if not same:
                print(f"MISMATCH: expected `{expected_path}` vs actual `{actual_path}`")
                print_delta(str(expected_path), str(actual_path))
            assert same, f"generated file `{actual_path}` does not match expected `{expected_path}`"
            if verbose:
                print(f"✅ success on {actual_path.relative_to(actual_dir)}")
            files_compared += 1
    assert files_compared > 0, "no expected files found to compare"


def _repo_root_from_here() -> Path:
    # packages/curvtools/test/curvtools/cache_tool/test_cache_tool.py → repo root is parents[5]
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


def test_outputs_match_expected_combined(tmp_path: Path):
    here = Path(__file__).parent
    vectors_root = here / "test_vectors" / "cache_tool4"
    input_dir = vectors_root / "input"
    expected_dir = vectors_root / "expected"

    out_dir = tmp_path / "out-combined"
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "curvtools.cli.cache_tool.cache_tool4",
        str(input_dir / "icache_dcache_combined.hex"),
        "-o", str(out_dir),
        "-e", str(input_dir / "curv-config.env"),
        "--no-hex-file-addresses",
        "--combined-icache-dcache",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, env=_py_env_with_workspace())
    assert result.returncode == 0, f"Command failed: {result.stderr}"

    # README
    expected_readme = expected_dir / "cache_readme.txt"
    actual_readme = out_dir / "cache_readme.txt"
    assert expected_readme.exists() and actual_readme.exists()
    same = filecmp.cmp(str(expected_readme), str(actual_readme), shallow=False)
    if not same:
        print_delta(str(expected_readme), str(actual_readme))
    assert same, "cache_readme.txt does not match expected output"

    _compare_trees(expected_dir, out_dir)


def test_outputs_match_expected_separate(tmp_path: Path):
    here = Path(__file__).parent
    vectors_root = here / "test_vectors" / "cache_tool4"
    input_dir = vectors_root / "input"
    expected_dir = vectors_root / "expected"

    out_dir = tmp_path / "out-separate"
    out_dir.mkdir(parents=True, exist_ok=True)

    # icache only
    cmd_i = [
        sys.executable, "-m", "curvtools.cli.cache_tool.cache_tool4",
        str(input_dir / "icache.hex"),
        "-o", str(out_dir),
        "-e", str(input_dir / "curv-config.env"),
        "--no-hex-file-addresses",
        "--icache-only",
    ]
    result = subprocess.run(cmd_i, capture_output=True, text=True, env=_py_env_with_workspace())
    assert result.returncode == 0, f"I$ command failed: {result.stderr}"

    # dcache only (override base address to 0x300 like original test)
    cmd_d = [
        sys.executable, "-m", "curvtools.cli.cache_tool.cache_tool4",
        str(input_dir / "dcache.hex"),
        "-o", str(out_dir),
        "-e", str(input_dir / "curv-config.env"),
        "--no-hex-file-addresses",
        "--dcache-only",
        "--base-address", "0x300",
    ]
    result = subprocess.run(cmd_d, capture_output=True, text=True, env=_py_env_with_workspace())
    assert result.returncode == 0, f"D$ command failed: {result.stderr}"

    # README
    expected_readme = expected_dir / "cache_readme.txt"
    actual_readme = out_dir / "cache_readme.txt"
    assert expected_readme.exists() and actual_readme.exists()
    same = filecmp.cmp(str(expected_readme), str(actual_readme), shallow=False)
    if not same:
        print_delta(str(expected_readme), str(actual_readme))
    assert same, "cache_readme.txt does not match expected output"

    _compare_trees(expected_dir, out_dir)


