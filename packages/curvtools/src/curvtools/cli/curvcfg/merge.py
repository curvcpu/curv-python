from __future__ import annotations
from pathlib import Path
from curvtools.cli.curvcfg.lib.curv_paths.curvcontext import CurvContext
from curvtools.cli.curvcfg.cli_helpers.paramtypes import ProfileResolvable
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import FsPathType
from curvtools.cli.curvcfg.lib.curv_paths import CurvPaths
from curvtools.cli.curvcfg.lib.globals.console import console
from curvtools.cli.curvcfg.lib.util.config_parsing.combine_merge_tomls import (
    combine_tomls,
    merge_tomls,
)
from curvtools.cli.curvcfg.lib.util.artifact_emitter import emit_merged_toml_and_dep_file


def merged_cfgvars_impl(
    curvctx: CurvContext,
    profile: ProfileResolvable,
    schemas: list[FsPathType],
    overlays: list[Path],
    merged_cfgvars_out_path: Path,
    dep_file_out: Path,
    is_tb: bool = False,
) -> None:
    curvpaths: CurvPaths = curvctx.curvpaths
    assert curvpaths is not None, "curvpaths not found in context object"
    verbosity = int(curvctx.args.get("verbosity", 0))
    # is_tb is reserved for future testbench-specific handling

    # 1) combine all the schemas without overlays
    schema_tomls_path_list = [x for x in schemas if x is not None]
    assert all(schema_toml.is_absolute() for schema_toml in schema_tomls_path_list), "all schema_tomls must be absolute paths"
    assert all(str(schema_toml.resolve()) == str(schema_toml) for schema_toml in schema_tomls_path_list), "all schema_tomls must already be resolved"
    combined_schema = combine_tomls(schema_tomls_path_list)

    # 2) merge the profile.toml with any overlays (later overlays override earlier)
    profile_toml_path = profile.resolve(curvpaths).path
    overlay_path_list: list[Path] = [Path(p).resolve() for p in overlays if p is not None]
    assert all(p.is_absolute() for p in overlay_path_list), "all overlay paths must be absolute paths"
    assert all(str(p.resolve()) == str(p) for p in overlay_path_list), "all overlay paths must already be resolved"
    merged_cfgvars = merge_tomls([profile_toml_path, *overlay_path_list])

    # 3) get the paths we will be writing
    dep_file_out_path = Path(dep_file_out)

    # 4) for the merge step, write concatenated schema + merged cfgvars and emit dep file
    assert merged_cfgvars_out_path.is_absolute(), "merged_cfgvars_out_path must be an absolute path"
    assert dep_file_out_path.is_absolute(), "dep_file_out_path must be an absolute path"
    assert str(merged_cfgvars_out_path.resolve()) == str(merged_cfgvars_out_path), "merged_cfgvars_out_path must already be resolved"
    assert str(dep_file_out_path.resolve()) == str(dep_file_out_path), "dep_file_out_path must already be resolved"

    merged_cfgvars_overwritten, dep_file_overwritten = emit_merged_toml_and_dep_file(
        curvpaths=curvpaths,
        combined_schema=combined_schema,
        schema_src_paths=schema_tomls_path_list,
        merged_config=merged_cfgvars,
        config_src_paths=[profile_toml_path, *overlay_path_list],
        merged_toml_out_path=merged_cfgvars_out_path,
        mk_dep_out_path=dep_file_out_path,
        verbosity=verbosity,
        overwrite_only_if_changed=True,
        header_comment=None,
    )

    # debug output
    if verbosity >= 1:
        if merged_cfgvars_overwritten:
            console.print(f"[bright_yellow]wrote:[/bright_yellow] {CurvPaths.mk_rel_to_cwd(merged_cfgvars_out_path)}")
        else:
            console.print(f"[green]unchanged:[/green] {CurvPaths.mk_rel_to_cwd(merged_cfgvars_out_path)}")
        if dep_file_overwritten:
            console.print(f"[bright_yellow]wrote:[/bright_yellow] {CurvPaths.mk_rel_to_cwd(dep_file_out_path)}")
        else:
            console.print(f"[green]unchanged:[/green] {CurvPaths.mk_rel_to_cwd(dep_file_out_path)}")
