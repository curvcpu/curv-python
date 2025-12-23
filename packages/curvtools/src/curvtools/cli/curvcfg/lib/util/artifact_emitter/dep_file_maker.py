from curvpyutils.file_utils import open_write_iff_change
from pathlib import Path
from typing import Optional
from curvtools.cli.curvcfg.lib.curv_paths import CurvPaths


__all__ = ["emit_dep_file"]

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


def emit_dep_file(
    target_path: Path, 
    dependency_paths: list[Path], 

    dep_file_out_path: Path, 

    curvpaths: CurvPaths,
    header_comment: Optional[str] = None,

    write_only_if_changed: bool = True,
    verbosity: int = 0,
) -> bool:
    """
    Generic .mk.d file emitter.

    Args:
        target_path: the path to the target file (input Path)
        dependency_paths: the list of dependency paths (input list[Path])
        dep_file_out_path: the path to the output dependency file (input Path)
        curvpaths: the curvpaths object (input CurvPaths)
        header_comment: an optional header comment to add to the top of the dependency file (input str)
        write_only_if_changed: whether to write only if the file has changed (default True)
        verbosity: the verbosity level (input int)

    Returns:
        True if the file was overwritten, False if it was not. (output bool)
    """
    if not target_path or not dependency_paths or not dep_file_out_path or not curvpaths:
        raise ValueError("required arguments are missing")

    target_path_str = _replace_path_with_make_var(target_path, curvpaths)
    dep_paths_str_list = [_replace_path_with_make_var(p, curvpaths) for p in dependency_paths]

    s = """
# Machine-generated file; do not edit
"""
    if header_comment:
        s += f"\n# {header_comment}\n"

    s += "\n"
    s += f"{target_path_str}: \\\n"
    for i, p in enumerate(dep_paths_str_list):
        is_last = i == len(dep_paths_str_list) - 1
        if is_last:
            s += f"  {p}\n"
        else:
            s += f"  {p} \\\n"

    cm = open_write_iff_change(dep_file_out_path, "w", force_overwrite=not write_only_if_changed)
    with cm as f:
        f.write(s)
        f.write("\n\n")

    return bool(cm.changed)
