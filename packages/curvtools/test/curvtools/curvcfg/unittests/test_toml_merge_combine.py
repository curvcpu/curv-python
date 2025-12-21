from __future__ import annotations

from pathlib import Path
import sys

import pytest
pytestmark = [pytest.mark.unit]

from curvtools.cli.curvcfg.lib.util.config_parsing.combine_merge_tomls import merge_tomls, combine_tomls

def _several_overlay_toml_paths() -> list[Path]:
    """
    Build paths to the several_overlay_tomls fixture set, relative to this file.
    """
    # .../curvcfg/unittests/test_toml_merge_combine.py
    curvcfg_dir = Path(__file__).resolve().parent.parent
    base_dir = curvcfg_dir / "unittests" / "test_vectors" / "inputs" / "merge_combine"
    return [
        base_dir / "base.toml",
        base_dir / "overlay1.toml",
        base_dir / "overlay2.toml",
        base_dir / "overlay3.toml",
    ]


def test_merge_combine_tomls_overlay_mode():
    paths = _several_overlay_toml_paths()

    result = merge_tomls(paths)

    # Expected result based on manual run of the helper script.
    assert result == {
        "cpu": {
            "mtvec_base": "0x00ff_abcd",
            "reset_vector": "0x0000_00ab",
            "xlen": 128,
        },
        "description": "Default configuration for the Curv RISCV SoC\n",
    }


def test_merge_combine_tomls_union_mode_conflict():
    paths = _several_overlay_toml_paths()

    with pytest.raises(KeyError) as excinfo:
        combine_tomls(paths)

    msg = str(excinfo.value)
    # We expect a conflict on the cpu.xlen key with differing values.
    assert "xlen" in msg
    assert "32" in msg
    assert "64" in msg

