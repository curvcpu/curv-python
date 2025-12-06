from __future__ import annotations
from pathlib import Path
from typing import List, Optional
from curvtools.cli.curvcfg.lib.curv_paths.curvcontext import CurvContext
from curvtools.cli.curvcfg.cli_helpers.paramtypes import BoardResolvable, DeviceResolvable
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import FsPathType
from curvtools.cli.curvcfg.lib.globals.curvpaths import CurvPaths
from curvtools.cli.curvcfg.cli_helpers.opts import FsPathType
from curvtools.cli.curvcfg.lib.globals.console import console
from curvtools.cli.curvcfg.lib.util.config_parsing.combine_merge_tomls import combine_tomls, merge_tomls
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
    merged_board_toml_overwritten = emit_merged_board_toml(combined_schema, merged_board_toml, merged_board_toml_out_path)
    # pprint(merged_board_toml)


    # debug output
    if verbosity >= 1:
        if merged_board_toml_overwritten:
            console.print(f"[bright_yellow]wrote:[/bright_yellow] {merged_board_toml_out_path}")
        else:
            console.print(f"[green]unchanged:[/green] {merged_board_toml_out_path}")

    # 5) emit the dep file
    dep_file_contents = get_dep_file_contents(merged_board_toml_out_path, schema_tomls_path_list, board_toml_path, device_toml_path, curvpaths)
    dep_file_overwritten = emit_dep_file(dep_file_out_path, dep_file_contents, write_only_if_changed=True)

    # debug output
    if verbosity >= 1:
        if dep_file_overwritten:
            console.print(f"[bright_yellow]wrote:[/bright_yellow] {dep_file_out_path}")
        else:
            console.print(f"[green]unchanged:[/green] {dep_file_out_path}")

def emit_merged_board_toml(combined_schema: dict, merged_board_config_toml: dict, merged_board_toml_out_path: Path, header_comment: Optional[str] = None, write_only_if_changed: bool = True):
    """
    Write the merged board configuration TOML file to a file, with optional header comment. The file 
    will contain the combined schema and the merged board configuration.

    Args:
        combined_schema: the combined schema (input dict[str, Any])
        merged_board_config_toml: the merged board configuration (input dict[str, Any])
        merged_board_toml_out_path: the path to the output TOML file (output Path)
        header_comment: an optional header comment to add to the top of the merged board configuration TOML file (input str)
        write_only_if_changed: whether to write only if the file has changed (default True)

    Returns:
        True if the file was overwritten, False if it was not. (output bool)
    """
    import tempfile
    import os
    import filecmp
    from curvpyutils.toml_utils import dump_dict_to_toml_str, TomlCanonicalizer

    general_header_comment = """
########################################################
# Machine-generated file; do not edit
########################################################

"""

    schema_header_comment = """

########################################################
#
# Schema section
#
########################################################

"""
    merged_board_config_header_comment = """

########################################################
#
# Configuration section
#
########################################################

"""

    merged_board_toml_out_path.parent.mkdir(parents=True, exist_ok=True)

    use_temp_file = write_only_if_changed and os.path.exists(merged_board_toml_out_path)
    
    # Create a temporary file for comparison if write_only_if_changed is True
    if use_temp_file:
        temp_fd, path_to_write = tempfile.mkstemp(suffix='.toml', prefix='curvcfg_')
        os.close(temp_fd)  # Close the file descriptor, we'll use the path
    else:
        path_to_write = str(merged_board_toml_out_path)
    
    # Write the merged TOML dict to the temporary file
    with open(path_to_write, "w") as f:
        if header_comment and header_comment.strip():
            f.write(header_comment.strip("\n") + "\n\n")
        f.write(general_header_comment)
        f.write(merged_board_config_header_comment)
        f.write(dump_dict_to_toml_str(merged_board_config_toml))
        f.write(schema_header_comment)
        f.write(dump_dict_to_toml_str(combined_schema))
        f.write("\n")

    TomlCanonicalizer(path_to_write, silent=True).overwrite_input_file()

    # Compare the temporary file to the original file
    if use_temp_file:
        if filecmp.cmp(path_to_write, merged_board_toml_out_path, shallow=False):
            # delete the temp file if it is the same as the original
            os.remove(path_to_write)
            # return False since the original was not touched
            return False
        else:
            # the file was changed, so we need to overwrite the original file and return True
            os.rename(path_to_write, merged_board_toml_out_path)
            return True
    else:
        # no temp file used, so we've already overwritten the original file
        return True


def _replace_path_with_make_var(path: Path, curvpaths: CurvPaths) -> str:
    """
    Replace the directory portion of an absolute path with the longest matching make variable
    from curvpaths, keeping the filename visible for readability.

    Args:
        path: the absolute path to transform (input Path)
        curvpaths: the curvpaths object (input CurvPaths) containing available make variables

    Returns:
        The path with the longest matching prefix replaced by $(VAR_NAME), or the original 
        path string if no match is found. The filename is always preserved.
    """
    path_str = str(path)
    
    # Build a list of (var_name, resolved_dir_path) for all fully resolved entries
    # We only want directory paths, so we'll treat each resolved path as a potential directory prefix
    resolved_vars: list[tuple[str, str]] = []
    for var_name, curvpath in curvpaths.items():
        if curvpath.is_fully_resolved():
            resolved_path = str(curvpath)
            # Ensure the path ends without a trailing slash for consistent matching
            resolved_path = resolved_path.rstrip('/')
            resolved_vars.append((var_name, resolved_path))
    
    # Also add the base curvpaths attributes (curv_root_dir and build_dir) as they may not be in the dict
    if curvpaths.curv_root_dir is not None:
        resolved_vars.append(('CURV_ROOT_DIR', str(curvpaths.curv_root_dir).rstrip('/')))
    if curvpaths.build_dir is not None:
        resolved_vars.append(('BUILD_DIR', str(curvpaths.build_dir).rstrip('/')))
    
    # Sort by path length (descending) so we find the longest match first
    resolved_vars.sort(key=lambda x: len(x[1]), reverse=True)
    
    # Get the directory portion of the path (everything except the filename)
    path_dir = str(path.parent)
    filename = path.name
    
    # Find the longest matching prefix for the directory portion
    best_match_var = None
    best_match_remainder = None
    
    for var_name, var_path in resolved_vars:
        # Check if the directory portion starts with this variable's path
        if path_dir == var_path:
            # Exact match for the directory - this is the best case
            best_match_var = var_name
            best_match_remainder = ""
            break
        elif path_dir.startswith(var_path + '/'):
            # The directory starts with this variable's path
            remainder = path_dir[len(var_path):]  # Will start with '/'
            best_match_var = var_name
            best_match_remainder = remainder
            break
    
    if best_match_var is not None:
        if best_match_remainder:
            return f"$({best_match_var}){best_match_remainder}/{filename}"
        else:
            return f"$({best_match_var})/{filename}"
    else:
        # No match found, return the original path
        return path_str


def get_dep_file_contents(merged_board_toml_out_path: Path, schema_tomls_path_list: list[Path], board_toml_path: Path, device_toml_path: Path, curvpaths: CurvPaths) -> str:
    """
    Generate the contents of a Makefile-style dependency fragment for merged_board.toml. It depends on all the schema tomls, 
    plus the board.toml and device.toml.

    Args:
        merged_board_toml_out_path: the path to the merged board TOML file (input Path)
        schema_tomls_path_list: the list of schema TOML files (input list[Path])
        board_toml_path: the path to the board TOML file (input Path)
        device_toml_path: the path to the device TOML file (input Path)
        curvpaths: the curvpaths object (input CurvPaths). This is used to replace absolute paths with make variables.

    Returns:
        The contents of the dependency file (output str)
    """
    # Convert all paths to make-variable-prefixed strings
    target_path = _replace_path_with_make_var(merged_board_toml_out_path, curvpaths)
    schema_paths = [_replace_path_with_make_var(p, curvpaths) for p in schema_tomls_path_list]
    board_path = _replace_path_with_make_var(board_toml_path, curvpaths)
    device_path = _replace_path_with_make_var(device_toml_path, curvpaths)

    s = ""
    s += f"{target_path}: \\\n"
    for schema_path in schema_paths:
        s += f"  {schema_path} \\\n"
    s += f"  {board_path} \\\n"
    s += f"  {device_path}\n"
    s += "\n"
    
    return s

def emit_dep_file(dep_file_out_path: Path, contents: str, write_only_if_changed: bool = True) -> bool:
    """
    Emit the dependency file to the given path.
    """
    import tempfile
    import os
    import filecmp

    general_header_comment = """
########################################################
# Machine-generated file; do not edit
########################################################

"""

    dep_file_out_path.parent.mkdir(parents=True, exist_ok=True)
    use_temp_file = write_only_if_changed and os.path.exists(dep_file_out_path)

    # Create a temporary file for comparison if write_only_if_changed is True
    if use_temp_file:
        temp_fd, path_to_write = tempfile.mkstemp(suffix='.dep', prefix='curvcfg_')
        os.close(temp_fd)  # Close the file descriptor, we'll use the path
    else:
        path_to_write = str(dep_file_out_path)

    with open(path_to_write, "w") as f:
        f.write(general_header_comment)
        f.write(contents)

    # Compare the temporary file to the original file
    if use_temp_file:
        if filecmp.cmp(path_to_write, dep_file_out_path, shallow=False):
            # delete the temp file if it is the same as the original
            os.remove(path_to_write)
            # return False since the original was not touched
            return False
        else:
            # the file was changed, so we need to overwrite the original file and return True
            os.rename(path_to_write, dep_file_out_path)
            return True
    else:
        # no temp file used, so we've already overwritten the original file
        return True
