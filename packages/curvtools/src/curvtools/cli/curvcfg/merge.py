from __future__ import annotations
import os
from typing import Callable, List
from pathlib import Path
from curvtools.cli.curvcfg.lib.globals.curvpaths import get_curv_paths
from curvpyutils.file_utils import DirWalker
from curvpyutils.toml_utils import MergedTomlDict  # type: ignore
from curvtools.cli.curvcfg.lib.util import get_config_values
from curvtools.cli.curvcfg.lib.globals.console import console
from curvtools.cli.curvcfg.lib.globals.types import CurvCliArgs
from curvtools.cli.curvcfg.lib.util.draw_tables import display_toml_tree, display_merged_toml_table, display_dep_file_contents
from curvtools.cli.curvcfg.lib.globals.constants import DEFAULT_OVERLAY_TOML_NAME

###############################################################################
#
# Find TOML helpers
#
###############################################################################

def find_overlay_tomls_abs_paths(root_dir: str, sub_dir: str, f_match_overlay_tomls: Callable[[str], bool]) -> list[str]:
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
    sub_dir_resolved = sub_dir.resolve()
    default_name = overlay_toml_name

    assert overlay_prefix=="", "overlay_prefix must be empty"
    assert overlay_toml_name==DEFAULT_OVERLAY_TOML_NAME, "overlay_toml_name must be " + DEFAULT_OVERLAY_TOML_NAME + " but was " + overlay_toml_name

    def matcher(dir_path: Path, entries: List[str], name: str) -> bool:
        # Restrict to the starting directory when no ascending is requested
        if no_ascend_dir_hierarchy and Path(dir_path).resolve() != sub_dir_resolved:
            return False
        else:
            return name == default_name
    return matcher

def _resolve_profile_file_path(profile_file_arg: str) -> Path:
    if not os.path.isfile(profile_file_arg):
        raise FileNotFoundError(f"Profile file {profile_file_arg} not found")
    return Path(profile_file_arg).resolve()

def _resolve_schema_path(schema_toml_arg: str) -> Path:
    if not os.path.isfile(schema_toml_arg):
        raise FileNotFoundError(f"Schema TOML {schema_toml_arg} not found")
    return Path(schema_toml_arg).resolve()

def _resolve_overlay_path_list(overlay_path_list: List[Optional[str]]) -> List[Path]:
    ret = [Path(path).resolve() for path in overlay_path_list if path is not None]
    if len(ret) == 0:
        # this should never happen because the default is [., None]
        raise ValueError("--overlay-path must be specified at least once")
    return ret

def _mk_tomls_list(
    profile_file: Path, 
    overlay_path_list: List[Path],
    overlay_toml_name: str,
    overlay_prefix: str,
    no_ascend_dir_hierarchy: bool
) -> list[str]:
    """
    Make the complete list of TOML files to merge.

    Args:
        profile_file: the profile file path
        overlay_path_list: the list of overlay path list items
        overlay_toml_name: the name of the overlay TOML file
        overlay_prefix: the prefix for overlay files
        no_ascend_dir_hierarchy: whether to not ascend directory hierarchy

    Returns:
        A list of TOML file paths
    """

    # if there is only one item in the list, then we are doing a directory hierarchy search
    if len(overlay_path_list) == 1:
        # if there is only one item in the list, then verify it is a directory
        if not overlay_path_list[0].is_dir():
            raise ValueError("--overlay-path must be a directory, not a file, unless it is used multiple times")

        # Build overlay matcher according to CLI args
        matcher = _make_overlay_matcher(
            sub_dir=overlay_path_list[0],
            overlay_toml_name=overlay_toml_name,
            overlay_prefix=overlay_prefix,
            no_ascend_dir_hierarchy=no_ascend_dir_hierarchy,
        )

        # Determine search bounds
        search_root_dir = get_curv_paths().get_repo_dir()
        if no_ascend_dir_hierarchy:
            search_root_dir = str(overlay_path_list[0])

        # Find overlay files (absolute paths)
        overlay_files: list[str] = find_overlay_tomls_abs_paths(
            root_dir=str(search_root_dir),
            sub_dir=str(overlay_path_list[0]),
            f_match_overlay_tomls=matcher,  # type: ignore[arg-type]
        )
    else:
        # if there is more than one item in the list, then we are doing a file specific search
        # so we just return the list of paths after verifying they are not directories
        for path in overlay_path_list:
            if path.is_dir():
                raise ValueError("--overlay-path must be a file, not a directory, when it is used multiple times")
        overlay_files: list[Path] = overlay_path_list

    # Build final tomls list: base first (lowest precedence), then overlays in order
    final_tomls_list: list[str] = [str(profile_file)] + [str(p) for p in overlay_files]
    return final_tomls_list

###############################################################################
#
# Helper to get the list of overlay tomls that apply in this context
#
###############################################################################

def get_tomls_list(
    profile_file: str,
    overlay_path_list: List[Optional[str]],
    overlay_toml_name: str,
    overlay_prefix: str = "",
    no_ascend_dir_hierarchy: bool = False
) -> list[str]:
    """
    Get the list of TOML files to merge.

    Args:
        profile_file: the profile file path
        overlay_path_list: the list of overlay path list items
        overlay_toml_name: the name of the overlay TOML file
        overlay_prefix: the prefix for overlay files (ALWAYS "" now)
        # combine_overlays: whether to combine overlays
        no_ascend_dir_hierarchy: whether to not ascend directory hierarchy

    Returns:
        A list of TOML file paths
    """
    # get the profile file
    profile_file_path = _resolve_profile_file_path(profile_file)

    # this should never happen because the default is [., None]
    assert not all(item is None for item in overlay_path_list), "overlay_path_list must be non-empty"

    # get the overlay path list
    overlay_path_list_resolved = _resolve_overlay_path_list(overlay_path_list)

    # make the list of TOML files to merge
    tomls_list = _mk_tomls_list(
        profile_file=profile_file_path,
        overlay_path_list=overlay_path_list_resolved,
        overlay_toml_name=overlay_toml_name,
        overlay_prefix=overlay_prefix,
        no_ascend_dir_hierarchy=no_ascend_dir_hierarchy
    )
    
    return tomls_list


###############################################################################
#
# Dep fragment file helper
#
###############################################################################

def mk_dep_file_contents(merged_toml_name: str, build_dir: str, tomls_list: list[str], verbosity: int = 0) -> str:
    """
    Generate the dep fragment file.
    
    Args:
        merged_toml_name: the output merged TOML file name
        build_dir: the build directory
        tomls_list: the list of TOML files to merge
        verbosity: the verbosity level
    Returns:
        string: contents of the dep fragment file
    """
    # Dep fragment: replace the root directory with $(CURV_ROOT_DIR)
    def repl_root(p: str) -> str:
        p_abs = str(Path(p))
        if p_abs.startswith(str(get_curv_paths().get_curv_root_dir())):
            return "$(CURV_ROOT_DIR)/" + get_curv_paths().mk_rel_to_curv_root(p_abs)
        return p_abs

    # Build list of targets to generate (relative to generated dir)
    build_generated_dir = repl_root(str(Path(build_dir) / "generated"))
    build_config_dir_abs = str(Path(build_dir) / "config")
    build_config_dir = repl_root(build_config_dir_abs)

    # Determine which file types to include based on runtime flags
    from curvtools.cli.curvcfg.lib.util import ConfigFileTypes, ConfigFileTypesForWriting, DEFAULT_OUTFILE_NAMES

    flag_to_key = {
        ConfigFileTypes.MAKEFILE: "makefile",
        ConfigFileTypes.ENV: "env",
        ConfigFileTypes.SVPKG: "svpkg",
        ConfigFileTypes.SVH: "svh",
        ConfigFileTypes.JSON: "json",
    }

    targets: list[str] = []
    for flag, key in flag_to_key.items():
        if ConfigFileTypesForWriting & flag:
            # Only include if we have a known output filename mapping
            outname = DEFAULT_OUTFILE_NAMES.get(key)
            if outname:
                targets.append(str(Path(build_generated_dir) / outname))

    # Targets to be generated
    all_targets = targets

    ret_str:str = ""

    # BUILD_CFG_GEN_DIR assignment using $(CURV_ROOT_DIR)
    ret_str += f"BUILD_GEN_DIR    := {build_generated_dir}\n\n"
    ret_str += f"BUILD_CONFIG_DIR := {build_config_dir}\n\n"

    # Dep fragment: replace build config dir with $(BUILD_CONFIG_DIR)
    def repl_build_config_dir(p: str) -> str:
        p_abs = str(Path(p))
        if p_abs.startswith(build_config_dir_abs):
            return "$(BUILD_CONFIG_DIR)/" + str(Path(p_abs).relative_to(Path(build_config_dir_abs)))
        return p_abs

    # Left-hand targets remain under BUILD_CFG_GEN_DIR
    target_strs = " ".join(
        f"$(BUILD_GEN_DIR)/{Path(t).name}" for t in all_targets
    )

    # Build dependency list: output merged.toml and all input tomls
    deps_list: list[str] = []
    if os.sep in merged_toml_name:
        merged_toml_file_name = os.path.basename(merged_toml_name)
    else:
        merged_toml_file_name = merged_toml_name
    deps_list.append(repl_build_config_dir(os.path.join(build_config_dir_abs, merged_toml_file_name)))
    deps_list.extend(repl_root(p) for p in tomls_list)

    # Write wrapped dependency rule for readability (GNU make compatible)
    ret_str += f"{target_strs}: \\\n"
    for i, dep in enumerate(deps_list):
        is_last = i == len(deps_list) - 1
        if is_last:
            ret_str += f"  {dep}\n"
        else:
            ret_str += f"  {dep} \\\n"

    return ret_str

def _write_dep_file(path: str, contents: str, write_only_if_changed: bool = True) -> bool:
    """
    Write the dep fragment file.

    Args:
        path: the path to the dep fragment file
        contents: the contents of the dep fragment file
        write_only_if_changed: whether to write only if the file has changed

    Returns:
        True if the file was overwritten, False if it was not.
    """
    import tempfile
    import os
    import filecmp
    
    # Determine if we need to use a temporary file for comparison
    use_temp_file = write_only_if_changed and os.path.exists(path)
    
    if use_temp_file:
        temp_fd, path_to_write = tempfile.mkstemp(suffix='.dep', prefix='curvcfg_')
        os.close(temp_fd)  # Close the file descriptor, we'll use the path
    else:
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Use the original path
        path_to_write = path
    
    with open(path_to_write, "w") as f:
        f.write(contents)
    
    if use_temp_file:
        if filecmp.cmp(path_to_write, path):
            # delete the temp file if it is the same as the original
            os.remove(path_to_write)
            # return False since the original file was not touched
            return False
        else:
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            # Overwrite the original file with the temporary file
            os.rename(path_to_write, path)
            # return True since the original file was overwritten
            return True
    else:
        # No temp file used => we've already overwritten the original file so return True
        return True

###############################################################################
#
# merge command entry point
#
###############################################################################

def merge(args: CurvCliArgs) -> int:
    """
    Merge overlays and a base config to generate output files.
    This is the entry point to the toml merge command.

    Args:
        args: the parsed args

    Returns:
        The exit code.
    """

    get_curv_paths(args)

    verbosity = int(args.get("verbosity", 0) or 0)

    # get the list of TOML files to merge
    assert args.get("overlay_toml_name")==DEFAULT_OVERLAY_TOML_NAME, "overlay_toml_name must be " + DEFAULT_OVERLAY_TOML_NAME + " but was " + args.get("overlay_toml_name")
    assert args.get("overlay_prefix")=="", "overlay_prefix must be empty but was " + args.get("overlay_prefix")
    tomls_list = get_tomls_list(
        profile_file=args.get("profile_file"),
        overlay_path_list=args.get("overlay_path_list"),
        overlay_toml_name=str(args.get("overlay_toml_name", "overlay.toml")),
        overlay_prefix=str(args.get("overlay_prefix", "")),
        no_ascend_dir_hierarchy=not bool(args.get("ascend_dir_hierarchy", True))
    )

    # Merge TOMLs into a dictionary
    merged = MergedTomlDict.from_toml_files(tomls_list[0], tomls_list[1:])

    if verbosity >= 1:
        display_toml_tree(tomls_list, use_ascii_box=False, verbosity=verbosity)

    # Remove top-level 'description' if present
    if isinstance(merged, dict) and "description" in merged:
        try:
            del merged["description"]
        except Exception:
            pass

    # Build CFG_ values from schema and merged TOML
    schema_toml_path = _resolve_schema_path(str(args.get("schema_file")))
    config_values = get_config_values(merged, schema_toml_path, is_combined_toml=False)

    # get output dir path
    build_dir = args.get("build_dir")
    merged_toml_output_dir = os.path.dirname(args.get("merged_file"))
    dep_file_output_dir = os.path.dirname(args.get("dep_file"))
    os.makedirs(merged_toml_output_dir, exist_ok=True)
    os.makedirs(dep_file_output_dir, exist_ok=True)

    # If schema file and base config file are the same file, then we don't want to append the schema data to
    # the end of the merged TOML so we can use it during the generate step.
    if args.get("schema_file") != args.get("profile_file"):
        schema_append_path = args.get("schema_file")
    else:
        schema_append_path = None

    # Unconditionally write output TOML
    merged_toml_overwritten = merged.write_to_file(
        args.get("merged_file"), 
        write_only_if_changed=True, 
        append_contents_of_file=schema_append_path)

    if verbosity >= 1:
        display_merged_toml_table(config_values, get_curv_paths().mk_rel_to_cwd(args.get("merged_file")), use_ascii_box=False, verbosity=verbosity)

    # Unconditionally write dep fragment file
    s = mk_dep_file_contents(args.get("merged_file"), build_dir, tomls_list, verbosity)
    dep_file_overwritten = _write_dep_file(args.get("dep_file"), s, write_only_if_changed=True)
    if verbosity >= 2:
        display_dep_file_contents(s, args.get("dep_file"), use_ascii_box=False)
    
    if verbosity >= 1:
        rel_path_out_toml = get_curv_paths().mk_rel_to_cwd(args.get("merged_file"))
        rel_path_dep_file = get_curv_paths().mk_rel_to_cwd(args.get("dep_file"))
        if merged_toml_overwritten:
            console.print(f"[bright_yellow]wrote:[/bright_yellow] {rel_path_out_toml}")
        else:
            console.print(f"[green]unchanged:[/green] {rel_path_out_toml}")
        if dep_file_overwritten:
            console.print(f"[bright_yellow]wrote:[/bright_yellow] {rel_path_dep_file}")
        else:
            console.print(f"[green]unchanged:[/green] {rel_path_dep_file}")

    return 0
