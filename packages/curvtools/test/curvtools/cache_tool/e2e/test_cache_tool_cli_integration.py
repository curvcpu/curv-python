#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path
import pytest
from curvpyutils import test_helpers

pytestmark = [pytest.mark.e2e]


def _load_config_toml(config_path: Path) -> dict:
    try:
        import tomllib as toml  # py311+
    except ModuleNotFoundError:
        import tomli as toml  # py310 fallback
    with open(config_path, "rb") as f:
        return toml.load(f)


def _repo_root_from_here() -> Path:
    # packages/curvtools/test/curvtools/cache_tool/e2e/test_cache_tool_cli_integration.py → repo root parents[6]
    return Path(__file__).resolve().parents[6]


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


def _compare_trees(expected_dir: Path, actual_dir: Path) -> None:
    files_compared = 0
    for root, _dirs, files in os.walk(expected_dir):
        for f in files:
            expected_path = Path(root) / f
            rel = expected_path.relative_to(expected_dir)
            actual_path = actual_dir / rel
            assert actual_path.exists(), f"missing generated file: {actual_path}"
            same = test_helpers.compare_files(str(expected_path), str(actual_path), verbose=True, show_delta=True)
            assert same, f"generated file `{actual_path}` does not match expected `{expected_path}`"
            files_compared += 1
    assert files_compared > 0, "no expected files found to compare"


def test_cache_tool_on_local_vectors(tmp_path: Path):
    here = Path(__file__).parent
    vectors = here / "test_vectors"
    input_dir = vectors / "input"
    expected_dir = vectors / "expected"

    text_hex = input_dir / "text-section.hex"
    data_hex = input_dir / "data-section.hex"
    expected_icache = expected_dir / "icache"
    expected_dcache = expected_dir / "dcache"
    expected_readme = expected_dir / "cache_readme.txt"

    assert text_hex.exists() and data_hex.exists(), "Input hex files missing"
    assert expected_icache.exists() and expected_dcache.exists(), "Expected cache dirs missing"
    assert expected_readme.exists(), "Expected cache_readme.txt missing"

    # Config (from the user's merged.toml snippet)
    sets = 4
    ways = 2
    addr_width = 27
    tags_have_vd = 0
    num_words = 16
    initially_valid = 1
    latency = 0
    icache_sub = "icache"
    dcache_sub = "dcache"
    cachelines_sub = "cachelines"
    tagram_sub = "tagram"

    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    common_args = [
        "--num-sets", str(sets),
        "--num-ways", str(ways),
        "--address-width", str(addr_width),
        "--cachelines-num-words", str(num_words),
        "--cachelines-latency", str(latency),
        "--icache-subdir", icache_sub,
        "--dcache-subdir", dcache_sub,
        "--cachelines-subdir", cachelines_sub,
        "--tagram-subdir", tagram_sub,
        "--no-hex-file-addresses",
    ]
    if initially_valid:
        common_args += ["--cachelines-initially-valid"]
    else:
        common_args += ["--no-cachelines-initially-valid"]
    if tags_have_vd:
        common_args += ["--tags-have-valid-dirty-bits"]
    else:
        common_args += ["--no-tags-have-valid-dirty-bits"]

    env = _py_env_with_workspace()

    # icache-only
    cmd_i = [
        sys.executable, "-m", "curvtools.cli.cache_tool.cache_tool4",
        str(text_hex),
        "-o", str(out_dir),
        "--icache-only",
        "--base-address", "0x00000100",  # I$ starts at 0x00000100
        *common_args,
    ]
    res = subprocess.run(cmd_i, capture_output=True, text=True, env=env)
    assert res.returncode == 0, f"I$ generation failed: {res.stderr}"

    # dcache-only
    cmd_d = [
        sys.executable, "-m", "curvtools.cli.cache_tool.cache_tool4",
        str(data_hex),
        "-o", str(out_dir),
        "--dcache-only",
        "--base-address", "0x00000300",  # D$ starts after I$ region in combined layout
        *common_args,
    ]
    res = subprocess.run(cmd_d, capture_output=True, text=True, env=env)
    assert res.returncode == 0, f"D$ generation failed: {res.stderr}"

    # Generate interleaved.bin for both I$ and D$
    interleave_jobs = [
        (out_dir / icache_sub / tagram_sub, expected_icache / "tagram"),
        (out_dir / dcache_sub / tagram_sub, expected_dcache / "tagram"),
    ]
    for actual_tagram_dir, _expected_tagram_dir in interleave_jobs:
        way0 = actual_tagram_dir / "way0.hex"
        way1 = actual_tagram_dir / "way1.hex"
        out_bin = actual_tagram_dir / "interleaved.bin"
        cmd_il = [
            sys.executable, "-m", "curvtools.cli.cache_tool.tag_ram_way_interleaver",
            str(way0), str(way1),
            "-o", str(out_bin),
        ]
        res = subprocess.run(cmd_il, capture_output=True, text=True, env=env)
        assert res.returncode == 0, f"Interleaver failed: {res.stderr}"

    # README comparison (show delta on mismatch)
    actual_readme = out_dir / "cache_readme.txt"
    assert actual_readme.exists()
    assert test_helpers.compare_files(str(expected_readme), str(actual_readme), verbose=True, show_delta=True), "cache_readme.txt mismatch"

    # Compare trees
    _compare_trees(expected_icache, out_dir / icache_sub)
    _compare_trees(expected_dcache, out_dir / dcache_sub)


