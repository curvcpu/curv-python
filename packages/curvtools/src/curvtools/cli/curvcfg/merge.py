from __future__ import annotations
import os
from typing import Callable, Iterable, List, Optional
from pathlib import Path
from curvtools.cli.curvcfg.lib.globals.curvpaths import get_curv_paths
from curvpyutils.toml_utils import MergedTomlDict, CombinedTomlDict
from curvtools.cli.curvcfg.lib.util import get_config_values
from curvtools.cli.curvcfg.lib.globals.console import console
from curvtools.cli.curvcfg.lib.globals.types import CurvCliArgs
from curvtools.cli.curvcfg.lib.util.draw_tables import (
    display_merged_toml_table,
    display_dep_file_contents,
)
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import FsPathType
from curvtools.cli.curvcfg.lib.util.file_emitter import (
    _emit_dep_file_contents,
    _emit_dep_file,
)

def merge(args: CurvCliArgs, ctx_obj: dict) -> int:
    """
    Merge one or more toml files to create a merged TOML. Each toml file listed overrides settings in the previous toml files, with the last taking the highest precedence.

    Args:
        args: the parsed args
        ctx_obj: the context object

    Returns:
        The exit code.
    """

    curv_paths: CurvPaths = ctx_obj.get("CurvPaths")
    assert curv_paths is not None, "CurvPaths not found in context object"

    verbosity = int(args.get("verbosity", 0) or 0)

    # get the list of TOML files to merge
    profile_file = args.get("profile_file")
    assert profile_file is not None, "profile_file is required"
    assert profile_file.is_absolute(), "profile_file must be an absolute path"
    assert str(profile_file.resolve())==str(profile_file), "profile_file must be already be resolved"
    profile_name = profile_file.stem
    overlay_path_list = args.get("overlay_path_list")
    if len(overlay_path_list) > 0 and all (overlay_path is not None for overlay_path in overlay_path_list):
        assert all(overlay_path.is_absolute() for overlay_path in overlay_path_list), "all overlay paths must be absolute paths"
        assert all(str(overlay_path.resolve())==str(overlay_path) for overlay_path in overlay_path_list), "all overlay paths must be already be resolved"

    # Merge TOMLs into a dictionary
    merged = MergedTomlDict(profile_file, [overlay_path for overlay_path in overlay_path_list])

    # Remove top-level 'description' if present
    if isinstance(merged, dict) and "description" in merged:
        try:
            del merged["description"]
        except Exception:
            pass

    # Build CFG_ values from schema and merged TOML
    schema_tomls_path_list = [x for x in args.get("schema_file_list") if x is not None]
    assert all(schema_toml.is_absolute() for schema_toml in schema_tomls_path_list), "all schema_tomls must be absolute paths"
    assert all(str(schema_toml.resolve())==str(schema_toml) for schema_toml in schema_tomls_path_list), "all schema_tomls must be already be resolved"
    config_values = get_config_values(merged, schema_tomls_path_list, is_combined_toml=False)

    # get output dir path
    build_dir = args.get("build_dir")
    assert build_dir.is_absolute(), "build_dir must be an absolute path"
    assert str(build_dir.resolve())==str(build_dir), "build_dir must be already be resolved"
    merged_toml_output_dir = args.get("merged_file").parent.resolve()
    assert merged_toml_output_dir.is_absolute(), "merged_toml_output_dir must be an absolute path"
    assert str(merged_toml_output_dir.resolve())==str(merged_toml_output_dir), "merged_toml_output_dir must be already be resolved"
    dep_file_output_dir = args.get("dep_file").parent.resolve()
    assert dep_file_output_dir.is_absolute(), "dep_file_output_dir must be an absolute path"
    assert str(dep_file_output_dir.resolve())==str(dep_file_output_dir), "dep_file_output_dir must be already be resolved"
    
    # create the dirs
    build_dir.mkdir(parents=True, exist_ok=True)
    merged_toml_output_dir.mkdir(parents=True, exist_ok=True)
    dep_file_output_dir.mkdir(parents=True, exist_ok=True)

    # If schema file and base config file are the same file, then we don't want to append the schema data to
    # the end of the merged TOML so we can use it during the generate step.
    if (len(schema_tomls_path_list) != 1) or (str(schema_tomls_path_list[0]) != str(args.get("profile_file"))):
        combined_schema_dict = CombinedTomlDict(schema_tomls_path_list)
        merged.append_dict(combined_schema_dict)

    # Write output TOML
    merged_toml_overwritten = merged.write_to_file(
        args.get("merged_file"), 
        write_only_if_changed=True
    )

    # Create a lambda that will take an absolute path and return it relative to
    # CURV_ROOT_DIR
    mk_rel_to_curv_root_dir = lambda p: curv_paths.mk_rel_to_curv_root(str(p))

    # Unconditionally write dep fragment file
    # Note how we have asserted that every path being passed into the two dep_*
    # functions is both absolute and resolved.
    curv_root_dir = curv_paths.get_curv_root_dir()
    assert args.get("merged_file").is_absolute(), "merged_file must be an absolute path"
    assert str(args.get("merged_file").resolve())==str(args.get("merged_file")), "merged_file must be already be resolved"
    dep_contents = _emit_dep_file_contents(
        merged_toml_name=args.get("merged_file"),
        build_dir=build_dir,
        tomls_list=[profile_file] + [overlay_path for overlay_path in overlay_path_list],
        curv_root_dir=curv_root_dir,
        verbosity=verbosity,
    )
    assert args.get("dep_file").is_absolute(), "dep_file must be an absolute path"
    assert str(args.get("dep_file").resolve())==str(args.get("dep_file")), "dep_file must be already be resolved"
    dep_file_overwritten = _emit_dep_file(
        path=args.get("dep_file"),
        contents=dep_contents,
        write_only_if_changed=True,
        verbosity=verbosity,
    )
    if verbosity >= 2:
        display_dep_file_contents(
            contents=dep_contents,
            target_path=args.get("dep_file"),
            use_ascii_box=False
        )
    
    if verbosity >= 1:
        rel_path_out_toml = args.get("merged_file").mk_rel_to_cwd()
        rel_path_dep_file = args.get("dep_file").mk_rel_to_cwd()
        if merged_toml_overwritten:
            console.print(f"[bright_yellow]wrote:[/bright_yellow] {rel_path_out_toml}")
        else:
            console.print(f"[green]unchanged:[/green] {rel_path_out_toml}")
        if dep_file_overwritten:
            console.print(f"[bright_yellow]wrote:[/bright_yellow] {rel_path_dep_file}")
        else:
            console.print(f"[green]unchanged:[/green] {rel_path_dep_file}")

    return 0
