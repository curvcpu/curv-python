from enum import Enum
from pathlib import Path
import sys
import os
from typing import Dict, Optional, Union
import click
from curvtools.cli.curvcfg.lib.globals.constants import PROGRAM_NAME, PACKAGE_NAME
from curvtools.cli.curvcfg.version import get_styled_version, get_styled_version_message
from curvtools.cli.curvcfg.cli_helpers import shell_complete_curv_root_dir
from curvtools.cli.curvcfg.cli_helpers.help_formatter import CurvcfgGroup, CurvcfgCommand
from curvtools.cli.curvcfg.lib.globals.curvpaths import get_curv_paths
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import FsPathType
from curvtools.cli.curvcfg.lib.util.draw_tables import display_args_table, display_curvcfg_settings_table
from curvtools.cli.curvcfg.lib.globals.constants import DEFAULT_MERGED_TOML_NAME, PROGRAM_NAME
from curvtools.cli.curvcfg.lib.globals.curvpaths import get_curv_paths
from curvtools.cli.curvcfg.cli_helpers import (
    BaseConfigAndSchemaMode,
    get_base_config_and_schema_mode,
    build_dir_opt,
    merged_toml_opt,
    verbosity_opts,
    overlay_opts,
    output_dep_opt,
    base_config_file_opt,
    schema_file_opt,
)
from .generate import generate as _generate_impl
from .show import (
    show_profiles as _show_profiles_impl, 
    show_active_variables as _show_active_variables_impl,
    show_overlays as _show_overlays_impl
)
from .merge import merge as _merge_impl
from .completions import completions as _completions_impl, determine_program_name
from curvtools.cli.curvcfg.lib.globals.types import CurvCliArgs
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import FsPathType

"""
Usage:
  curvcfg [--curv-root-dir=<curv-root-dir>] merge    --base-config-file=<base-config-file> [--schema-file=<schema-file>] [--overlay-dir=<overlay-dir>] [--build-dir=<build-dir>] [--merged-toml-outfile=<merged-toml-outfile>] [--dep-file-outfile=<dep-file-outfile>] [--no-ascend-dir-hierarchy] [--overlay-prefix=<overlay-prefix>] [--combine-overlays]
  curvcfg [--curv-root-dir=<curv-root-dir>] generate --build-dir=<build-dir>               [--merged-toml-infile=<merged-toml-infile>]
  curvcfg                                   completions                                    [--shell=<shell>] [--install|--print] [--path=<path>]
  curvcfg [--curv-root-dir=<curv-root-dir>] show profiles
  curvcfg [--curv-root-dir=<curv-root-dir>] show vars --build-dir=<build-dir>              [--merged-toml-infile=<merged-toml-infile>]

General options (apply to all commands):
  --curv-root-dir=<curv-root-dir> Normally, we use CURV_ROOT_DIR from the environment, but this option will override it. (Default: use CURV_ROOT_DIR from the environment)
  --verbose                       Enables verbose mode.  Up to 3 times.
  --version                       Show the version and exit.
  -h, --help                      Show this message and exit.

merge command options:
  Base options:
  --base-config-file=<base-config-file>        (required) Path to the base config file to merge.  Default is either <curv-root-dir>/config/default.toml or <curv-root-dir>/config/profiles/default.toml, depending on the base config and schema mode.
  --schema-file=<schema-file>                  (required) Path to schema TOML file. Default is $CURV_ROOT_DIR/config/schema/schema.toml or <curv-root-dir>/config/schema.toml, depending on the base config and schema mode.
  --build-dir=<build-dir>                      Base build directory. Outputs are written under this directory. Default is "build/" relative to the cwd.
  --merged-toml-outfile=<merged-toml-outfile>  Where to write merged.toml output file. Default is "<build-dir>/config/merged.toml".
  --dep-file-outfile=<dep-file-outfile>        Where to write the Makefile dependency file. Default is "<build-dir>/make.deps/config.mk.d".
  --overlay-no-ascend-dirs                     Do not ascend directories when searching for overlay toml files; only consider the overlay directory. Default is False.
  --overlay-dir=<overlay-dir>                  The lowest directory that contains an overlay.toml file. Default is cwd. May be relative to cwd, or absolute.
  --overlay-toml-name=<overlay-toml-name>      The base name of overlay toml files. Default is "overlay.toml".
  --overlay-prefix=<overlay-prefix>            A prefix that can be used to select between different overlay toml files. Default is empty.
  --overlay-combine                            If a directory contains both a `<prefix>.overlay.toml` and an `overlay.toml` file, use both, with the prefixed file taking precedence. Default is True.
  --include-out-toml-in-deps                   Include the output merged.toml in the dependencies listed in the Makefile dependency file. Default is True.

completions command options:
  --shell=<shell>  Shell to generate completions for. Defaults to current shell.
  --install/--print  Install completions script to default path, or print to stdout.
  --path=<path>  Custom install path for the completions script.

generate command options:
  --build-dir=<build-dir>                      Base build directory. Outputs are written under "<build-dir>/generated". Default is "build/" relative to the cwd.
  --merged-toml-infile=<merged-toml-infile>    The merged config TOML filename to read from. Default is "<build-dir>/config/merged.toml" if not provided.

show command options:
  --repo-root-dir=<repo-root-dir>               Override the repository folder location (must exist). Default is git-rev-parse root relative to the cwd.
        ------------------------------------------------------------
        show vars command options
        ------------------------------------------------------------
        --build-dir=<build-dir>          Base build directory. Used to locate active merged config TOML by default, unless --config-toml is provided. Default is "build/" relative to the cwd.
        --config-toml=<config-toml>      Path to merged config TOML; if relative, resolved against CWD. Default is "<build-dir>/config/merged.toml".

Environment variables:
  CURV_ROOT_DIR  The root of the curv project. If set, it must exist. Otherwise, it defaults to <repo-root-dir>/my-designs/riscv-soc (repo-root-dir from --repo-root-dir or git repo root).
"""

from curvpyutils.shellutils import get_console_width
CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
    # "max_content_width": get_console_width(),
}

def _resolved_dist_name() -> str:
    try:
        top = __package__.split('.')[0]
        return ilmd.packages_distributions().get(top, [top])[0]
    except Exception:
        return PACKAGE_NAME


@click.group(
    cls=CurvcfgGroup,
    context_settings=CONTEXT_SETTINGS,
    epilog=None,
)
@click.version_option(
    version=get_styled_version(),
    message=get_styled_version_message(),
    prog_name=PROGRAM_NAME,
    package_name=_resolved_dist_name(),
)
@click.option(
    "--curv-root-dir",
    "curv_root_dir",
    metavar="<curv-root-dir>",
    default=os.environ.get("CURV_ROOT_DIR"),
    show_default=True,
    help=(
        "Overrides CURV_ROOT_DIR found from the environment or git-rev-parse."
    ),
    envvar="CURV_ROOT_DIR",
    shell_complete=shell_complete_curv_root_dir,
)
@verbosity_opts(include_verbose=True)
@click.pass_context
def cli(
    ctx: click.Context,
    curv_root_dir: Optional[str],
    verbose: int,
) -> None:
    """curvcfg command line interface"""
    ctx.ensure_object(dict)
    ctx.obj["curv_root_dir"] = curv_root_dir
    ctx.obj["verbosity"] = max(ctx.obj.get("verbosity", 0), min(verbose, 3))

@cli.command(
    cls=CurvcfgCommand,
    context_settings=CONTEXT_SETTINGS,
    short_help="Merge base config and overlays",
    help="Merge base config and overlays into a merged TOML (in <build-dir>/config/merged.toml by default) and a Makefile dependency file (in <build-dir>/make.deps/config.mk.d by default)"
)
@base_config_file_opt(required=True)
@schema_file_opt(required=True)
@build_dir_opt(help="Base build directory; outputs written under this directory")
@overlay_opts()
@merged_toml_opt(name="out_toml", outfile=True)
@output_dep_opt()
@click.option(
    "--include-out-toml-in-deps",
    "include_out_toml_in_deps",
    is_flag=True,
    default=True,
    help="Include the output merged.toml in the dependencies list in the config.mk.d.",
)
@verbosity_opts(include_verbose=True)
@click.pass_context
def merge(
    ctx: click.Context,
    base_config_file: FsPathType,
    schema_file: FsPathType,
    build_dir: str,
    overlay_dir: str,
    overlay_toml_base_name: str,
    overlay_prefix: str,
    combine_overlays: bool,
    ascend_dir_hierarchy: bool,
    out_toml: Optional[str],
    out_dep: Optional[str],
    include_out_toml_in_deps: bool,
    verbose: int,
) -> None:
    merge_args: CurvCliArgs = {
        "curv_root_dir": ctx.obj.get("curv_root_dir"),
        "base_config_file": base_config_file,
        "schema_file": schema_file,
        "build_dir": build_dir,
        "overlay_dir": overlay_dir,
        "overlay_toml_name": overlay_toml_base_name,
        "overlay_prefix": overlay_prefix,
        "combine_overlays": combine_overlays,
        "ascend_dir_hierarchy": ascend_dir_hierarchy,
        "out_toml": out_toml,
        "out_dep": out_dep,
        "include_out_toml_in_deps": include_out_toml_in_deps,
        "verbosity": max(ctx.obj["verbosity"], min(verbose, 2)),
    }

    if int(merge_args.get("verbosity", 0) or 0) >= 3:
        display_args_table(merge_args, "merge")
    _exit_code = _merge_impl(merge_args)
    raise SystemExit(_exit_code)

@cli.command(
    cls=CurvcfgCommand,
    context_settings=CONTEXT_SETTINGS,
    epilog=None,
)
@build_dir_opt(help="Base build directory; outputs written to this directory.  Also used to locate <merged-toml> by default, unless --merged-toml overrides with a specific path.")
@merged_toml_opt(name="merged_toml", outfile=False)
@schema_file_opt(required=True)
@verbosity_opts(include_verbose=True)
@click.pass_context
def generate(ctx: click.Context, build_dir: str, merged_toml: Optional[str], schema_file: FsPathType, verbose: int) -> None:
    """Generate output files from a merged TOML and schema."""
    generate_args: CurvCliArgs = {
        "curv_root_dir": ctx.obj.get("curv_root_dir"),
        "build_dir": os.path.abspath(build_dir),
        "merged_toml": merged_toml,
        "schema_file": schema_file,
        "verbosity": max(ctx.obj["verbosity"], min(verbose, 2)),
    }
    if int(generate_args.get("verbosity", 0) or 0) >= 3:
        display_args_table(generate_args, "generate")
    rc = _generate_impl(generate_args)
    raise SystemExit(rc)

def main(argv: Optional[list[str]] = None) -> int:
    try:
        cli.main(args=argv, standalone_mode=False)
    except click.exceptions.ClickException as exc:
        exc.show()
        return exc.exit_code
    except SystemExit as exc:
        return int(exc.code)
    return 0

@cli.command(name="completions", context_settings=CONTEXT_SETTINGS)
@click.option("--shell", "shell", type=click.Choice(["bash", "zsh", "fish", "powershell"]), default=None,
              help="Shell to generate completions for. Defaults to current shell.")
@click.option("--install/--print", "install", default=False,
              help="Install completion script to default path, or print to stdout.")
@click.option("--path", "install_path", default=None, metavar="<path>",
              help="Custom install path for the completion script.")
@click.pass_context
def completions(ctx: click.Context, shell: Optional[str], install: bool, install_path: Optional[str]) -> None:
    """Generate or install shell completion scripts for this CLI."""
    
    completions_args: CurvCliArgs = {
        "curv_root_dir": ctx.obj.get("curv_root_dir"),
        "verbosity": ctx.obj["verbosity"],
        "shell": shell,
        "install": install,
        "install_path": install_path,
    }
    prog_name = determine_program_name(ctx.command_path, ctx.info_name, "curvcfg")
    if int(completions_args.get("verbosity", 0) or 0) >= 3:
        display_args_table(completions_args, "completions")
    _exit_code = _completions_impl(completions_args, prog_name)
    raise SystemExit(_exit_code)




@cli.group(name="show", context_settings=CONTEXT_SETTINGS, help="Show active build configuration values and related information")
@verbosity_opts(include_verbose=True)
@click.pass_context
def show(ctx: click.Context, verbose: int) -> None:
    """Show active build configuration values and related information"""
    ctx.obj["verbosity"] = max(min(verbose, 3), ctx.obj.get("verbosity", 0))

@show.command(name="vars", context_settings=CONTEXT_SETTINGS,
    short_help="Show active configuration variables",
    help="Show active configuration variables that apply in the current build environment based on the <build-dir>/config/merged.toml file. If such a file does not exist, then nothing is shown.")
@build_dir_opt(help=(
    f"Base build directory; used to locate <merged-toml> "
    "by default, unless --merged-toml overrides with a specific "
    "path."
))
@base_config_file_opt(required=True)
@merged_toml_opt(name="merged_toml", outfile=False)
@verbosity_opts(include_verbose=True)
@click.pass_context
def show_active_variables(ctx: click.Context, build_dir: str, base_config_file: FsPathType, merged_toml: Optional[str], verbose: int) -> None:
    
    show_args: CurvCliArgs = {
        "curv_root_dir": ctx.obj.get("curv_root_dir"),
        "build_dir": build_dir,
        "base_config_file": base_config_file,
        "merged_toml": merged_toml,
        "verbosity": max(ctx.obj["verbosity"], min(verbose, 3)),
    }
        
    if int(show_args.get("verbosity", 0) or 0) >= 3:
        display_curvcfg_settings_table(ctx)
        display_args_table(show_args, "show")
    rc = _show_active_variables_impl(show_args)
    raise SystemExit(rc)

@show.command(
    context_settings=CONTEXT_SETTINGS,
    name="overlays", 
    short_help=f"Shows the hierarchy of base config + overlays",
    help=f"Shows the hierarchy of base config + overlays that generate the {DEFAULT_MERGED_TOML_NAME} in the current build environment")
@base_config_file_opt(required=True)
@overlay_opts()
@verbosity_opts(include_verbose=True)
@click.pass_context
def show_overlays(ctx: click.Context, base_config_file: FsPathType, overlay_dir: str, overlay_toml_base_name: str, overlay_prefix: str, combine_overlays: bool, ascend_dir_hierarchy: bool, verbose: int) -> None:
    show_args: CurvCliArgs = {
        "curv_root_dir": ctx.obj.get("curv_root_dir"),
        "base_config_file": base_config_file,
        "overlay_dir": overlay_dir,
        "overlay_toml_name": overlay_toml_base_name,
        "overlay_prefix": overlay_prefix,
        "combine_overlays": combine_overlays,
        "no_ascend_dir_hierarchy": not ascend_dir_hierarchy,
        "verbosity": max(ctx.obj["verbosity"], min(verbose, 3)),
    }
    if int(show_args.get("verbosity", 0) or 0) >= 3:
        display_args_table(show_args, "show")
    rc = _show_overlays_impl(show_args)
    raise SystemExit(rc)

@show.command(name="profiles", context_settings=CONTEXT_SETTINGS,
    short_help="Show available base configurations (profiles)",
    help="Show available base configurations in $CURV_ROOT_DIR/config/profiles directory",
    hidden=(get_base_config_and_schema_mode() == BaseConfigAndSchemaMode.BASE_CONFIG_AND_SCHEMA_IN_SINGLE_DIRECTORY),
)
@verbosity_opts(include_verbose=True)
@click.pass_context
def show_profiles(ctx: click.Context, verbose: int) -> None:
    """Show available base configurations"""

    show_args: CurvCliArgs = {
        "curv_root_dir": ctx.obj.get("curv_root_dir"),
        "verbosity": max(ctx.obj["verbosity"], min(verbose, 2)),
    }
    if int(show_args.get("verbosity", 0) or 0) >= 3:
        display_args_table(show_args, "show")
    rc = _show_profiles_impl(show_args)
    raise SystemExit(rc)

if __name__ == "__main__":
    sys.exit(main())
