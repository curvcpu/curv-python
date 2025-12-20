from __future__ import annotations
from pathlib import Path
from typing import Optional, Mapping, Any
from curvtools.cli.curvcfg.lib.curv_paths.curvcontext import CurvContext
from curvtools.cli.curvcfg.cli_helpers.paramtypes import ProfileResolvable
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import FsPathType
from curvtools.cli.curvcfg.lib.globals.curvpaths import CurvPaths
from curvtools.cli.curvcfg.lib.globals.console import console
from curvtools.cli.curvcfg.lib.util.artifact_emitter import emit_artifacts
from curvtools.cli.curvcfg.lib.util.config_parsing import schema_oracle_from_merged_toml


def generate_config_artifacts_impl(
    curvctx: CurvContext,
    merged_cfgvars_input_path: Path,
    svpkg_template: Optional[Path] = None,
    svh_template: Optional[Path] = None,
    mk_template: Optional[Path] = None,
    env_template: Optional[Path] = None,
    is_tb: bool = False,
) -> None:
    curvpaths: CurvPaths = curvctx.curvpaths
    assert curvpaths is not None, "curvpaths not found in context object"
    verbosity = int(curvctx.args.get("verbosity", 0))
    # is_tb is reserved for future testbench-specific handling

    # 1) read the merged config toml into a SchemaOracle
    schema_oracle: SchemaOracle = schema_oracle_from_merged_toml(merged_cfgvars_input_path)

    # 2) get names out output files
    cfgvars_pkg_out_path = curvpaths["CONFIG_SVPKG"].to_path()
    cfgvars_svh_out_path = curvpaths["CONFIG_SVH"].to_path()
    cfgvars_env_out_path = curvpaths["CONFIG_ENV"].to_path()
    cfgvars_mk_out_path = curvpaths["CONFIG_MK"].to_path()

    # 3) emit the artifacts
    emit_artifacts(
        schema_oracle,
        cfgvars_pkg_out_path,
        cfgvars_svh_out_path,
        cfgvars_env_out_path,
        cfgvars_mk_out_path,
        svpkg_template=svpkg_template,
        svh_template=svh_template,
        mk_template=mk_template,
        env_template=env_template,
    )

    # 4) print success message
    if verbosity >= 1:
        console.print(f"[green]Successfully generated configuration artifacts from <{merged_cfgvars_input_path}>[/green]")


def generate_board_artifacts_impl(
    curvctx: CurvContext,
    merged_board_input_path: Path,
    svpkg_template: Optional[Path] = None,
    svh_template: Optional[Path] = None,
    mk_template: Optional[Path] = None,
    env_template: Optional[Path] = None,
    is_tb: bool = False,
) -> None:
    curvpaths: CurvPaths = curvctx.curvpaths
    assert curvpaths is not None, "curvpaths not found in context object"
    verbosity = int(curvctx.args.get("verbosity", 0))
    # is_tb is reserved for future testbench-specific handling

    # 1) read the merged board toml into a dict[str, Any]
    schema_oracle: SchemaOracle = schema_oracle_from_merged_toml(merged_board_input_path)

    # 2) get names out output files
    board_pkg_out_path = curvpaths["BOARD_SVPKG"].to_path()
    board_svh_out_path = curvpaths["BOARD_SVH"].to_path()
    board_env_out_path = curvpaths["BOARD_ENV"].to_path()
    board_mk_out_path = curvpaths["BOARD_MK"].to_path()

    # 3) emit the board artifacts
    emit_artifacts(
        schema_oracle,
        board_pkg_out_path,
        board_svh_out_path,
        board_env_out_path,
        board_mk_out_path,
        svpkg_template=svpkg_template,
        svh_template=svh_template,
        mk_template=mk_template,
        env_template=env_template,
    )

    # 4) print success message
    if verbosity >= 1:
        console.print(f"[green]Successfully generated board artifacts from <{merged_board_input_path}>[/green]")
