from __future__ import annotations
import os
from typing import Callable, Iterable, List, Optional
from pathlib import Path
from curvpyutils.file_utils import DirWalker
from curvpyutils.toml_utils import MergedTomlDict, CombinedTomlDict
from curvtools.cli.curvcfg.lib.util import get_config_values
from curvtools.cli.curvcfg.lib.globals.console import console
from curvtools.cli.curvcfg.lib.globals.types import CurvCliArgs
from curvtools.cli.curvcfg.lib.util.draw_tables import (
    display_toml_tree,
    display_merged_toml_table,
    display_dep_file_contents,
)
from curvtools.cli.curvcfg.lib.globals.constants import DEFAULT_OVERLAY_TOML_NAME
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import FsPathType
from curvtools.cli.curvcfg.lib.util.file_emitter import (
    _emit_dep_file_contents,
    _emit_dep_file,
)
from curvtools.cli.curvcfg.lib.globals.curvpaths import CurvPaths

###############################################################################
#
# Find TOML helpers
#
###############################################################################

def find_overlay_tomls_abs_paths(root_dir: str|Path, sub_dir: str|Path, f_match_overlay_tomls: Callable[[str], bool]) -> list[str]:
    """
    Find all overlay.toml files in the directory tree starting from `sub_dir` and
    up to `root_dir`.
    
    Args:
        root_dir: The root directory to stop searching in.
        sub_dir: The directory to start searching in.
        f_match_overlay_tomls: a function that takes a file name and returns True/False to indicate a match

    Returns:
        A list of overlay.toml file absolute paths.
    """
    dirwalker = DirWalker(root_dir, sub_dir, f_match_overlay_tomls)
    rel_paths_list: list[str] = dirwalker.get_matching_files()
    return [str((Path(sub_dir) / path).resolve()) for path in rel_paths_list]

def _make_overlay_matcher(
    sub_dir: Path,
    overlay_toml_name: str,
    overlay_prefix: str,
    no_ascend_dir_hierarchy: bool,
) -> Callable[[Path, List[str], str], bool]:
    """Create a matcher for overlay files honoring CLI semantics.

    The matcher receives (dir_path, entries, name) and returns True if "name"
    in directory "dir_path" should be considered an overlay TOML per rules.
    """
    assert sub_dir.is_absolute(), "sub_dir must be an absolute path"
    default_name = overlay_toml_name
    assert overlay_prefix=="", "overlay_prefix must be empty"
    assert overlay_toml_name==DEFAULT_OVERLAY_TOML_NAME, "overlay_toml_name must be " + DEFAULT_OVERLAY_TOML_NAME + " but was " + overlay_toml_name

    def matcher(dir_path: Path, entries: List[str], name: str) -> bool:
        # Restrict to the starting directory when no ascending is requested
        if no_ascend_dir_hierarchy and Path(dir_path).resolve() != sub_dir:
            return False
        else:
            return name == default_name
    return matcher

# def _resolve_profile_file_path(profile_file_arg: str) -> Path:
#     if not os.path.isfile(profile_file_arg):
#         raise FileNotFoundError(f"Profile file {profile_file_arg} not found")
#     return Path(profile_file_arg).resolve()

# def _resolve_schema_path(schema_toml_arg: str) -> Path:
#     if not os.path.isfile(schema_toml_arg):
#         raise FileNotFoundError(f"Schema TOML {schema_toml_arg} not found")
#     return Path(schema_toml_arg).resolve()

# def _resolve_overlay_path_list(overlay_path_list: Iterable[Optional[str]] | Optional[FsPathType]) -> List[Path]:
#     if overlay_path_list is None:
#         normalized_paths: Iterable[Optional[str]] = []
#     elif isinstance(overlay_path_list, (list, tuple)):
#         normalized_paths = overlay_path_list
#     else:
#         normalized_paths = [overlay_path_list]
#     ret = [Path(path).resolve() for path in normalized_paths if path is not None]
#     if len(ret) == 0:
#         # this should never happen because the default is [., None]
#         raise ValueError("--overlay-path must be specified at least once")
#     return ret

def _mk_tomls_list(
    profile_file: FsPathType, 
    overlay_dir: FsPathType,
    overlay_toml_name: str,
    overlay_prefix: str,
    no_ascend_dir_hierarchy: bool,
    curv_paths: CurvPaths
) -> list[str]:
    """
    Make the complete list of TOML files to merge.

    Args:
        profile_file: the profile file path
        overlay_dir: the lowest directory path to look in for overlay toml files
        overlay_toml_name: the name of the overlay TOML file
        overlay_prefix: the prefix for overlay files
        no_ascend_dir_hierarchy: whether to not ascend directory hierarchy

    Returns:
        A list of TOML file paths
    """

    assert overlay_dir.is_dir(), "overlay_dir must be a directory"
    assert overlay_dir.is_absolute(), "overlay_dir must be an absolute path"

    # Build overlay matcher according to CLI args
    matcher = _make_overlay_matcher(
        sub_dir=overlay_dir,
        overlay_toml_name=overlay_toml_name,
        overlay_prefix=overlay_prefix,
        no_ascend_dir_hierarchy=no_ascend_dir_hierarchy,
    )

    # Determine search bounds
    search_root_dir = curv_paths.get_repo_dir()
    if no_ascend_dir_hierarchy:
        search_root_dir = overlay_dir

    # Find overlay files (absolute paths)
    overlay_files: list[str] = find_overlay_tomls_abs_paths(
        root_dir=search_root_dir,
        sub_dir=overlay_dir,
        f_match_overlay_tomls=matcher,  # type: ignore[arg-type]
    )
    # Always start with the base profile file, followed by any overlays discovered.
    tomls: list[str] = [str(profile_file)]
    tomls.extend(overlay_files)
    return tomls

###############################################################################
#
# Helper to get the list of overlay tomls that apply in this context
#
###############################################################################

def get_tomls_list(
    curv_paths: CurvPaths,
    profile_file: FsPathType,
    overlay_dir: FsPathType,
    overlay_toml_name: str,
    overlay_prefix: str = "",
    no_ascend_dir_hierarchy: bool = False,
) -> list[str]:
    """
    Get the list of TOML files to merge.

    Args:
        curv_paths: the curv paths
        profile_file: the profile file path
        overlay_dir: the lowest directory path to look in for overlay toml files
        overlay_toml_name: the name of the overlay TOML file
        overlay_prefix: the prefix for overlay files (ALWAYS "" now)
        # combine_overlays: whether to combine overlays
        no_ascend_dir_hierarchy: whether to not ascend directory hierarchy

    Returns:
        A list of TOML file paths
    """
    assert profile_file.is_absolute(), "profile_file must be an absolute path"
    assert overlay_dir.is_absolute(), "overlay_dir must be an absolute path"
    # make the list of TOML files to merge
    tomls_list = _mk_tomls_list(
        profile_file=profile_file,
        overlay_dir=overlay_dir,
        overlay_toml_name=overlay_toml_name,
        overlay_prefix=overlay_prefix,
        no_ascend_dir_hierarchy=no_ascend_dir_hierarchy,
        curv_paths=curv_paths
    )
    return tomls_list


###############################################################################
#
# merge command entry point
#
###############################################################################

def merge_tb(args: CurvCliArgs, ctx_obj: dict) -> int:
    """
    Merge overlays and a base config to generate output files.
    This is the entry point to the toml merge command.

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
    assert args.get("overlay_toml_name")==DEFAULT_OVERLAY_TOML_NAME, "overlay_toml_name must be " + DEFAULT_OVERLAY_TOML_NAME + " but was " + args.get("overlay_toml_name")
    assert args.get("overlay_prefix")=="", "overlay_prefix must be empty but was " + args.get("overlay_prefix")
    tomls_list = get_tomls_list(
        curv_paths=curv_paths,
        profile_file=args.get("profile_file"),
        overlay_dir=args.get("overlay_dir"),
        overlay_toml_name=str(args.get("overlay_toml_name", "overlay.toml")),
        overlay_prefix=str(args.get("overlay_prefix", "")),
        no_ascend_dir_hierarchy=not bool(args.get("ascend_dir_hierarchy", True)),
    )

    # Merge TOMLs into a dictionary
    merged = MergedTomlDict(tomls_list[0], tomls_list[1:])

    if verbosity >= 1:
        display_toml_tree(tomls_list, curv_paths=curv_paths, use_ascii_box=False, verbosity=verbosity)

    # Remove top-level 'description' if present
    if isinstance(merged, dict) and "description" in merged:
        try:
            del merged["description"]
        except Exception:
            pass

    # Build CFG_ values from schema and merged TOML
    schema_tomls_path_list = args.get("schema_file_list")
    assert all(isinstance(schema_toml_path, (str, Path)) for schema_toml_path in schema_tomls_path_list if schema_toml_path is not None), "all schema file paths must be strings or Path objects"
    assert all(os.path.isfile(schema_toml_path) and os.access(schema_toml_path, os.R_OK) for schema_toml_path in schema_tomls_path_list if schema_toml_path is not None), "all schema files must be found and readable"
    schema_tomls_path_list = [schema_toml_path for schema_toml_path in schema_tomls_path_list]
    config_values = get_config_values(merged, schema_tomls_path_list, is_combined_toml=False)

    # get output dir path
    build_dir = args.get("build_dir")
    merged_toml_output_dir = os.path.dirname(args.get("merged_file"))
    dep_file_output_dir = os.path.dirname(args.get("dep_file"))
    os.makedirs(build_dir, exist_ok=True)
    os.makedirs(merged_toml_output_dir, exist_ok=True)
    os.makedirs(dep_file_output_dir, exist_ok=True)

    # If schema file and base config file are the same file, then we don't want to append the schema data to
    # the end of the merged TOML so we can use it during the generate step.
    if (len(schema_tomls_path_list) == 1) and (schema_tomls_path_list[0] == args.get("profile_file")):
        pass
    else:
        combined_schema_dict = CombinedTomlDict(schema_tomls_path_list)
        merged.append_dict(combined_schema_dict)

    # Unconditionally write output TOML
    merged_toml_overwritten = merged.write_to_file(
        str(args.get("merged_file")), 
        write_only_if_changed=True)

    if verbosity >= 1:
        display_merged_toml_table(config_values, args.get("merged_file").mk_rel_to_cwd(), use_ascii_box=False, verbosity=verbosity)

    # Unconditionally write dep fragment file
    curv_root_dir = curv_paths.get_curv_root_dir()
    dep_contents = _emit_dep_file_contents(
        merged_toml_name=args.get("merged_file"),
        build_dir=build_dir,
        tomls_list=[Path(p) for p in tomls_list],
        curv_root_dir=curv_root_dir,
        verbosity=verbosity,
    )
    dep_file_overwritten = _emit_dep_file(
        path=args.get("dep_file"),
        contents=dep_contents,
        write_only_if_changed=True,
        verbosity=verbosity,
    )
    if verbosity >= 2:
        display_dep_file_contents(
            contents=dep_contents,
            target_path=str(args.get("dep_file")),
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
