from types import SimpleNamespace
from pathlib import Path

import pytest

from curvtools.cli.curvcfg.generate import (
    generate_config_artifacts_impl,
    generate_board_artifacts_impl,
)
from curvpyutils.test_helpers import compare_files

pytestmark = [pytest.mark.unit]


class DummyPath:
    def __init__(self, path: Path):
        self._path = Path(path)

    def to_path(self) -> Path:
        return self._path


class DummyCurvPaths(dict):
    def __getitem__(self, key: str) -> DummyPath:
        return super().__getitem__(key)


def _mk_curvpaths(base: Path, kind: str) -> DummyCurvPaths:
    if kind == "config":
        return DummyCurvPaths(
            {
                "CONFIG_SVPKG": DummyPath(base / "curvcfgpkg.sv"),
                "CONFIG_SVH": DummyPath(base / "curvcfg.svh"),
                "CONFIG_ENV": DummyPath(base / "curv.env"),
                "CONFIG_MK": DummyPath(base / "curv.mk"),
            }
        )
    if kind == "board":
        return DummyCurvPaths(
            {
                "BOARD_SVPKG": DummyPath(base / "boardpkg.sv"),
                "BOARD_SVH": DummyPath(base / "board.svh"),
                "BOARD_ENV": DummyPath(base / "board.env"),
                "BOARD_MK": DummyPath(base / "board.mk"),
            }
        )
    raise ValueError(kind)


def _compare_outputs(outputs, expecteds, label_prefix: str):
    failed = []
    for label, outp, exp in zip(label_prefix, outputs, expecteds):
        ok = compare_files(outp, exp, show_delta=True, verbose=True)
        if not ok:
            print(f"{label} output differed: {outp}")
            failed.append(outp)
    return failed


def test_generate_config_and_board(tmp_path: Path):
    base_vectors = Path(__file__).parents[1] / "test_vectors"
    inputs_dir = base_vectors / "inputs" / "test_generate"
    expected_dir = base_vectors / "expected" / "test_generate"

    merged_path = inputs_dir / "merged_schema_vars.toml"
    svpkg_template = inputs_dir / "sv_template.svpkg.jinja2"

    # ----- config: template svpkg -----
    config_curvpaths = _mk_curvpaths(tmp_path / "config", "config")
    config_ctx = SimpleNamespace(curvpaths=config_curvpaths, args={"verbosity": 0})

    generate_config_artifacts_impl(
        config_ctx,
        merged_cfgvars_input_path=merged_path,
        svpkg_template=svpkg_template,
    )

    tmpl_expected = expected_dir / "svpkg_from_template.svh"
    cmp_ok = compare_files(
        config_curvpaths["CONFIG_SVPKG"].to_path(),
        tmpl_expected,
        show_delta=True,
        verbose=True,
    )
    if not cmp_ok:
        print(f"Template svpkg output differed: {config_curvpaths['CONFIG_SVPKG'].to_path()}")
    assert cmp_ok

    # ----- config: default logic -----
    # regenerate without template into fresh paths
    config_curvpaths = _mk_curvpaths(tmp_path / "config_default", "config")
    config_ctx = SimpleNamespace(curvpaths=config_curvpaths, args={"verbosity": 0})
    generate_config_artifacts_impl(
        config_ctx,
        merged_cfgvars_input_path=merged_path,
    )

    outputs = [
        config_curvpaths["CONFIG_SVPKG"].to_path(),
        config_curvpaths["CONFIG_SVH"].to_path(),
        config_curvpaths["CONFIG_ENV"].to_path(),
        config_curvpaths["CONFIG_MK"].to_path(),
    ]
    expecteds = [
        expected_dir / "curvcfgpkg.sv",
        expected_dir / "curvcfg.svh",
        expected_dir / "curv.env",
        expected_dir / "curv.mk",
    ]
    labels = ["config_svpkg", "config_svh", "config_env", "config_mk"]
    failed = _compare_outputs(outputs, expecteds, labels)
    assert not failed

    # ----- board: default logic (no templates) -----
    board_curvpaths = _mk_curvpaths(tmp_path / "board_default", "board")
    board_ctx = SimpleNamespace(curvpaths=board_curvpaths, args={"verbosity": 0})
    generate_board_artifacts_impl(
        board_ctx,
        merged_board_input_path=merged_path,
    )

    board_outputs = [
        board_curvpaths["BOARD_SVPKG"].to_path(),
        board_curvpaths["BOARD_SVH"].to_path(),
        board_curvpaths["BOARD_ENV"].to_path(),
        board_curvpaths["BOARD_MK"].to_path(),
    ]
    board_expecteds = [
        expected_dir / "boardpkg.sv",
        expected_dir / "board.svh",
        expected_dir / "board.env",
        expected_dir / "board.mk",
    ]
    board_labels = ["board_svpkg", "board_svh", "board_env", "board_mk"]
    failed_board = _compare_outputs(board_outputs, board_expecteds, board_labels)
    assert not failed_board

    # Cleanup only if all asserts passed
    for p in (
        [config_curvpaths["CONFIG_SVH"].to_path()]
        + outputs
        + board_outputs
    ):
        if p.exists():
            p.unlink()
