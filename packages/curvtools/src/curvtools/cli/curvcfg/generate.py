from __future__ import annotations
import os
from typing import Optional, Dict, Union
from pathlib import Path
from curvtools.cli.curvcfg.lib.globals.console import console
from curvtools.cli.curvcfg.lib.globals.curvpaths import get_curv_paths
from curvpyutils.toml_utils import MergedTomlDict  # type: ignore
from curvtools.cli.curvcfg.lib.util import get_config_values, emit_config_files
from curvtools.cli.curvcfg.lib.globals.types import CurvCliArgs

def generate(args: CurvCliArgs) -> int:
    """
    Generate output files from a merged config TOML and a schema.

    Args:
        args: parsed CLI args

    Returns:
        Exit code
    """
    get_curv_paths(args)

    # Resolve inputs
    merged_toml_path = args.get("merged_file")
    

    # Validate readable input
    if not (os.path.isfile(merged_toml_path) and os.access(merged_toml_path, os.R_OK)):
        console.print(f"[red]error:[/red] merged toml not found or unreadable: {merged_toml_path}")
        return 1

    verbosity = int(args.get("verbosity", 0) or 0)

    try:
        merged = MergedTomlDict.from_toml_files(merged_toml_path)
        outdir_path = Path(args.get("build_dir")) / "generated"
    except Exception as exc:
        console.print(f"[red]error:[/red] failed reading merged config: {exc}")
        return 1

    # If merged already has schema information in it, then we don't need the separate schema file and will ignore it.
    if '_schema' not in merged.keys():
        # we need the file, so get it and validate it
        schema_file_path = args.get("schema_file")
        if not (os.path.isfile(schema_file_path) and os.access(schema_file_path, os.R_OK)):
            console.print(f"[red]error:[/red] schema file not found or unreadable: {schema_file_path}")
            return 1
        is_combined_toml = False
    else:
        schema_file_path = None
        is_combined_toml = True
    
    # Collect values and emit
    try:
        cfg_values = get_config_values(merged, schema_file_path, is_combined_toml=is_combined_toml)
        files_emitted, files_unchanged = emit_config_files(cfg_values, outdir_path=outdir_path, verbosity=verbosity)
        if verbosity == 1:
            for file in files_emitted:
                console.print(f"[green]emitted:[/green] {get_curv_paths().mk_rel_to_cwd(file)}")
            for file in files_unchanged:
                console.print(f"[yellow]unchanged:[/yellow] {get_curv_paths().mk_rel_to_cwd(file)}")
    except SystemExit:
        raise
    except Exception as exc:
        console.print(f"[red]error:[/red] generation failed: {exc}")
        return 1

    return 0
