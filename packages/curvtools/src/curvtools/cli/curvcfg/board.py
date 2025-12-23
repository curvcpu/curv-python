from __future__ import annotations
from pathlib import Path
from typing import List, Optional
from curvtools.cli.curvcfg.lib.curv_paths.curvcontext import CurvContext
from curvtools.cli.curvcfg.cli_helpers.paramtypes import BoardResolvable, DeviceResolvable
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import FsPathType
from curvtools.cli.curvcfg.lib.curv_paths import CurvPaths
from curvtools.cli.curvcfg.cli_helpers.opts import FsPathType
from curvtools.cli.curvcfg.lib.globals.console import console
from curvtools.cli.curvcfg.lib.util.config_parsing.combine_merge_tomls import (
    combine_tomls, 
    merge_tomls, 
)
from curvtools.cli.curvcfg.lib.util.artifact_emitter import emit_merged_toml_and_dep_file
from rich.pretty import pprint

def merge_board_impl(curvctx: CurvContext, board_name: BoardResolvable, device_name: DeviceResolvable, schemas: list[FsPathType], merged_board_toml_out_path: Path, dep_file_out: Path):    
    curvpaths: CurvPaths = curvctx.curvpaths
    assert curvpaths is not None, "curvpaths not found in context object"
    verbosity = int(curvctx.args.get("verbosity", 0))
    
    # 1) combine all the schema without overlays 
    schema_tomls_path_list = [x for x in schemas if x is not None]
    assert all(schema_toml.is_absolute() for schema_toml in schema_tomls_path_list), "all schema_tomls must be absolute paths"
    assert all(str(schema_toml.resolve())==str(schema_toml) for schema_toml in schema_tomls_path_list), "all schema_tomls must be already be resolved"
    combined_schema = combine_tomls(schema_tomls_path_list)
    # pprint(combined_schema)

    # 2) merge the board.toml and device.toml (the latter overrides)
    board_toml_path = board_name.resolve(curvpaths).path
    device_toml_path = device_name.resolve(curvpaths).path
    merged_board_toml = merge_tomls([board_toml_path, device_toml_path])
    # pprint(merged_board_toml)

    # 3) get the paths we will be writing
    # (paths are already resolved - merged_board_toml_out_path is a Path, dep_file_out is a string so we make it a Path)
    dep_file_out_path = Path(dep_file_out)

    # 4) create the output dirs
    assert merged_board_toml_out_path.is_absolute(), "merged_board_toml_out_path must be an absolute path"
    assert dep_file_out_path.is_absolute(), "dep_file_out_path must be an absolute path"
    assert str(merged_board_toml_out_path.resolve())==str(merged_board_toml_out_path), "merged_board_toml_out_path must be already be resolved"
    assert str(dep_file_out_path.resolve())==str(dep_file_out_path), "dep_file_out_path must be already be resolved"

    # 4) for the merge step, we simply want to write everything (concatenated schema + merged board config) to the output file
    # and emit the dep file
    merged_board_toml_overwritten, dep_file_overwritten = emit_merged_toml_and_dep_file(
        curvpaths=curvpaths,

        combined_schema=combined_schema,
        schema_src_paths=schema_tomls_path_list,
        merged_config=merged_board_toml,
        config_src_paths=[board_toml_path, device_toml_path],

        merged_toml_out_path=merged_board_toml_out_path,
        mk_dep_out_path=dep_file_out_path,
        verbosity=verbosity,
        overwrite_only_if_changed=True,
        header_comment=None,
    )

    # debug output
    if verbosity >= 1:
        if merged_board_toml_overwritten:
            console.print(f"[bright_yellow]wrote:[/bright_yellow] {CurvPaths.mk_rel_to_cwd(merged_board_toml_out_path)}")
        else:
            console.print(f"[green]unchanged:[/green] {CurvPaths.mk_rel_to_cwd(merged_board_toml_out_path)}")
        if dep_file_overwritten:
            console.print(f"[bright_yellow]wrote:[/bright_yellow] {CurvPaths.mk_rel_to_cwd(dep_file_out_path)}")
        else:
            console.print(f"[green]unchanged:[/green] {CurvPaths.mk_rel_to_cwd(dep_file_out_path)}")

