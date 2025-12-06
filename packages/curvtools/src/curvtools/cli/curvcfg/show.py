import os
import sys
from typing import Dict, Union
from curvtools.cli.curvcfg.lib.globals.console import console
from rich.table import Table
from curvtools.cli.curvcfg.lib.util import get_config_values
from curvtools.cli.curvcfg.lib.util.draw_tables import (
    display_merged_toml_table,
    display_profiles_table,
)
from curvtools.cli.curvcfg.lib.globals.curvpaths import CurvPaths
from pathlib import Path

def show_active_variables_impl(merged_toml_in_path: Path, curvpaths: CurvPaths, verbosity: int,  use_ascii_box: bool = False) -> int:
    """
    List the global configuration values that apply in the current environment.

    Args:
        args: parsed CLI args

    Returns:
        Exit code
    """

    # Get active config values from the build config TOML
    config_values = get_config_values(merged_toml_in_path, None, is_combined_toml=True)

    # Display the active config values
    display_merged_toml_table(config_values, CurvPaths.mk_rel_to_cwd(merged_toml_in_path), use_ascii_box=use_ascii_box, verbose_table=verbosity >= 2)

    return 0

def show_profiles_impl(curvpaths: CurvPaths, use_ascii_box: bool = False) -> int:
    """
    List the available profiles.

    Args:
        curvpaths: the curv paths instance
        use_ascii_box: whether to use ascii box

    Returns:
        Exit code
    """
    profiles_dir = curvpaths["CURV_CONFIG_PROFILES_DIR"].to_path()
    if not profiles_dir.exists():
        console.print(f"Profiles directory {profiles_dir} does not exist", style="bold red")
        return 1
    profile_name_and_path_list = [(p.stem, p) for p in profiles_dir.glob("*.toml") if p.is_file()]
    new_profile_name_and_path_list = []
    for i, (profile_name, profile_path) in enumerate(profile_name_and_path_list):
        try:
            new_profile_name_and_path_list.append((profile_name, Path("<CURV_ROOT_DIR>") / profile_path.relative_to(curvpaths.curv_root_dir)))
        except ValueError:
            new_profile_name_and_path_list.append((profile_name, profile_path))

    display_profiles_table(new_profile_name_and_path_list, curvpaths.curv_root_dir, use_ascii_box=use_ascii_box)
    return 0
