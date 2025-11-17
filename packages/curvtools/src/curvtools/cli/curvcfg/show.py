import os
import sys
from typing import Dict, Union
from curvtools.cli.curvcfg.lib.globals.console import console
from curvtools.cli.curvcfg.lib.globals.profiles import get_all_profiles #, get_active_profile_name
from rich.table import Table
from curvtools.cli.curvcfg.lib.globals.curvpaths import get_curv_paths
from curvtools.cli.curvcfg.lib.util import get_config_values
from curvtools.cli.curvcfg.merge import get_tomls_list
from curvtools.cli.curvcfg.lib.util.draw_tables import (
    display_toml_tree, 
    display_merged_toml_table
)
from curvtools.cli.curvcfg.lib.globals.types import CurvCliArgs
from curvtools.cli.curvcfg.lib.globals.constants import DEFAULT_OVERLAY_TOML_NAME

def show_profiles(args: CurvCliArgs) -> int:
    """
    List available profiles and overlays.

    Args:
        args: parsed CLI args

    Returns:
        Exit code
    """
    get_curv_paths(args)

    verbosity = int(args.get("verbosity", 0) or 0)

    profiles = get_all_profiles(get_curv_paths().get_config_dir(), sort_with_default_first=True)

    table = Table()
    table.add_column("Base Config Name")
    table.add_column("File Path")
    table.add_column("Description")
    for name,profile in profiles.items():
        profile_description = profile["description"].strip() if "description" in profile else "(no description)"
        table.add_row(f"[bright_blue]{name}[/bright_blue]", "$CURV_ROOT_DIR/" + get_curv_paths().mk_rel_to_curv_root(profile.toml_file()), profile_description)
    console.print(table)
    if len(profiles) == 0:
        print("no profiles found", file=sys.stderr)
        return 1
    
    return 0

def show_overlays(args: CurvCliArgs) -> int:
    """
    List the overlays that apply in the current environment.
    """
    get_curv_paths(args)

    verbosity = int(args.get("verbosity", 0) or 0)
    
    profile_file = str(args.get("profile_file"))
    
    assert args.get("overlay_toml_name")==DEFAULT_OVERLAY_TOML_NAME, "overlay_toml_name must be " + DEFAULT_OVERLAY_TOML_NAME + " but was " + args.get("overlay_toml_name")
    assert args.get("overlay_prefix")=="", "overlay_prefix must be empty but was " + args.get("overlay_prefix")
    tomls_list = get_tomls_list(
        profile_file=profile_file,
        overlay_path_list=args.get("overlay_path_list"),
        overlay_toml_name=str(args.get("overlay_toml_name", "overlay.toml")),
        overlay_prefix=str(args.get("overlay_prefix", "")),
        no_ascend_dir_hierarchy=bool(args.get("no_ascend_dir_hierarchy", False)))

    # +1 because it only displays if verbosity is at least 1
    display_toml_tree(tomls_list, verbosity=verbosity+1)
    
    return 0

def show_active_variables(args: CurvCliArgs, use_ascii_box: bool = False) -> int:
    """
    List the global configuration values that apply in the current environment.

    Args:
        args: parsed CLI args

    Returns:
        Exit code
    """
    get_curv_paths(args)

    # add 1 to verbosity since it won't display anything at zero
    verbosity = 1 + int(args.get("verbosity", 0) or 0)

    # Resolve inputs
    merged_toml_path = args.get("merged_file")
    
    # Validate readable inputs
    if not (os.path.isfile(merged_toml_path) and os.access(merged_toml_path, os.R_OK)):
        console.print(f"no merged toml found in '{merged_toml_path}'")
        console.print(f"Are you in the right directory?", style="bold yellow")
        console.print(f"Have you run `make` to generate the build subdirectory?", style="bold yellow")
        return 1
    
    # Get active config values from the build config TOML
    config_values = get_config_values(merged_toml_path, None, is_combined_toml=True)

    # Display the active config values
    display_merged_toml_table(config_values, get_curv_paths().mk_rel_to_cwd(merged_toml_path), verbosity=verbosity, use_ascii_box=use_ascii_box)

    # for high verbosity, we also show the tomls hierarchy if possible
    if verbosity >= 3:
        tomls_list = get_tomls_list(profile_file=args.get("profile_file"))
        display_toml_tree(tomls_list, verbosity=verbosity)

    return 0
