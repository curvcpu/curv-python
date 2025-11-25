import os
import sys
from typing import Dict, Union
from curvtools.cli.curvcfg.lib.globals.console import console
from rich.table import Table
from curvtools.cli.curvcfg.lib.util import get_config_values
from curvtools.cli.curvcfg.lib.util.draw_tables import (
    display_merged_toml_table
)
from curvtools.cli.curvcfg.lib.globals.types import CurvCliArgs

def show_active_variables(args: CurvCliArgs, ctx_obj: dict, use_ascii_box: bool = False) -> int:
    """
    List the global configuration values that apply in the current environment.

    Args:
        args: parsed CLI args

    Returns:
        Exit code
    """
    curv_paths: CurvPaths = ctx_obj.get("CurvPaths")
    assert curv_paths is not None, "CurvPaths not found in context object"

    # add 1 to verbosity since it won't display anything at zero
    verbosity = 1 + int(args.get("verbosity", 0) or 0)
    
    # Validate readable inputs
    if not args.get("merged_file").is_file() or not args.get("merged_file").is_readable():
        console.print(f"no merged toml found in '{str(args.get('merged_file'))}'")
        console.print(f"Are you in the right directory?", style="bold yellow")
        console.print(f"Have you run `make` to generate the build subdirectory?", style="bold yellow")
        return 1

    # Get active config values from the build config TOML
    config_values = get_config_values(args.get("merged_file"), None, is_combined_toml=True)

    # Display the active config values
    display_merged_toml_table(config_values, args.get("merged_file").mk_rel_to_cwd(), verbosity=verbosity, use_ascii_box=use_ascii_box)

    return 0
