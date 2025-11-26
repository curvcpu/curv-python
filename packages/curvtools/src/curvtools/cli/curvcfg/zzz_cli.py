from enum import Enum
from pathlib import Path
import sys
import os
from typing import Dict, Optional, Union, Callable, List
import click
from curvtools.cli.curvcfg.cli_helpers import shell_complete_curv_root_dir
from curvtools.cli.curvcfg.cli_helpers.help_formatter import CurvcfgHelpFormatterGroup, CurvcfgHelpFormatterCommand
from curvtools.cli.curvcfg.lib.globals.curvpaths import get_curv_paths, CurvPaths
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import FsPathType
from curvtools.cli.curvcfg.lib.util.draw_tables import display_args_table, display_tool_settings, display_curvpaths
from curvtools.cli.curvcfg.lib.globals.constants import DEFAULT_MERGED_TOML_NAME, DEFAULT_OVERLAY_TOML_NAME, DEFAULT_DEP_FILE_PATH, DEFAULT_MERGED_TOML_PATH
from curvtools.cli.curvcfg.cli_helpers import (
    build_dir_opt,
    overlay_opts_for_paths_list,
    merged_toml_input_opt,
    merged_toml_output_opt,
    verbosity_opts,
    output_dep_opt,
    schema_file_opt,
    profile_file_opt,
    version_opt,
    kind_opts,
    board_device_opts,
)
from .generate import generate as _generate_impl
from .show import (
    show_profiles as _show_profiles_impl, 
    show_active_variables as _show_active_variables_impl,
)
from .merge import merge as _merge_impl
from .completions import completions as _completions_impl, determine_program_name
from curvtools.cli.curvcfg.lib.globals.types import CurvCliArgs
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import FsPathType
from rich.traceback import install
from curvtools.cli.curvcfg.lib.globals.console import console
from curvpyutils.cli_util import preparse, EarlyArg
from curvtools.cli.curvcfg.cli_helpers.help_formatter.epilog import set_epilog_fn
from curvtools.cli.curvcfg.cli_helpers.opts.board_device_opts import Kind

"""
Usage:
  curvcfg [--curv-root-dir=<curv-root-dir>] merge    --profile-file=<profile-toml-file> [--schema-file=<schema-toml-file>] [--overlay-dir=<overlay-dir>] [--build-dir=<build-dir>] [--merged-file=<merged-toml-file-out>] [--dep-file=<dep-file-out>] [--no-ascend-dir-hierarchy] [--overlay-prefix=<overlay-prefix>] [--combine-overlays]
  curvcfg [--curv-root-dir=<curv-root-dir>] generate --build-dir=<build-dir>               [--merged-file=<merged-toml-file-in>]
  curvcfg                                   completions                                    [--shell=<shell>] [--install|--print] [--path=<path>]
  curvcfg [--curv-root-dir=<curv-root-dir>] show profiles
  curvcfg [--curv-root-dir=<curv-root-dir>] show vars --build-dir=<build-dir>              [--merged-file=<merged-toml-file-in>]

General options (apply to all commands):
  --curv-root-dir=<curv-root-dir> Normally, we use CURV_ROOT_DIR from the environment, but this option will override it. (Default: use CURV_ROOT_DIR from the environment)
  --verbose                       Enables verbose mode.  Up to 3 times.
  --version                       Show the version and exit.
  -h, --help                      Show this message and exit.

merge command options:
  Base options:
  --profile-file=<profile-toml-file>        (required) Path to the profile file to merge.  Default is either <curv-root-dir>/config/default.toml or <curv-root-dir>/config/profiles/default.toml, depending on the base config and schema mode.
  --schema-file=<schema-toml-file>                  (required) Path to schema TOML file. Default is $CURV_ROOT_DIR/config/schema/schema.toml or <curv-root-dir>/config/schema.toml, depending on the base config and schema mode.
  --build-dir=<build-dir>                      Base build directory. Outputs are written under this directory. Default is "build/" relative to the cwd.
  --merged-file=<merged-toml-file-out>  Where to write merged.toml output file. Default is "<build-dir>/config/merged.toml".
  --dep-file=<dep-file-out>        Where to write the Makefile dependency file. Default is "<build-dir>/make.deps/config.mk.d".
  --ascend-dir-hierarchy/--no-ascend-dir-hierarchy                     Do ascend directories when searching for overlay toml files; only consider the overlay directory. Default is True.
  --overlay-dir=<overlay-dir>                  The lowest directory that contains an overlay.toml file. Default is cwd. May be relative to cwd, or absolute.

completions command options:
  --shell=<shell>  Shell to generate completions for. Defaults to current shell.
  --install/--print  Install completions script to default path, or print to stdout.
  --path=<path>  Custom install path for the completions script.

generate command options:
  --build-dir=<build-dir>                      Base build directory. Outputs are written under "<build-dir>/generated". Default is "build/" relative to the cwd.
  --merged-file=<merged-toml-file-in>    The merged config TOML filename to read from. Default is "<build-dir>/config/merged.toml" if not provided.

show command options:
  --repo-root-dir=<repo-root-dir>               Override the repository folder location (must exist). Default is git-rev-parse root relative to the cwd.
        ------------------------------------------------------------
        show vars command options
        ------------------------------------------------------------
        --build-dir=<build-dir>          Base build directory. Used to locate active merged config TOML by default, unless --config-toml is provided. Default is "build/" relative to the cwd.
        --merged-file=<merged-toml-file-in>      Path to merged config TOML; if relative, resolved against CWD. Default is "<build-dir>/config/merged.toml".

Environment variables:
  CURV_ROOT_DIR  The root of the curv project. If set, it must exist. Otherwise, it defaults to <repo-root-dir>/my-designs/riscv-soc (repo-root-dir from --repo-root-dir or git repo root).
"""

from curvpyutils.shellutils import get_console_width
CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
    # "max_content_width": get_console_width(),
}

def update_curvpaths(
        ctx: click.Context,
        curv_root_dir: FsPathType|None = None,
        build_dir: FsPathType|None = None,
        profile: FsPathType|str|None = None,
        board: FsPathType|str|None = None,
        device: FsPathType|str|None = None,
        merged_toml_path: FsPathType|None = None,
    ) -> None:
    """
    Update the ctx.obj['CurvPaths'] object in the context object. Any argument except ctx can be None and it will be ignored.

    Args:
        ctx: The click context object.
        curv_root_dir: The CURV_ROOT_DIR to use.
        build_dir: The build directory to use.
        profile: The profile to use.
        board: The board to use.
        device: The device to use.
        merged_toml_path: The merged TOML path to use.

    Returns:
        None
    """
    ctx.ensure_object(dict)
    if 'CurvPaths' not in ctx.obj:
        ctx.obj['CurvPaths']: CurvPaths = get_curv_paths(ctx)
    kwargs = {}
    if curv_root_dir is not None:
        kwargs['curv_root_dir'] = str(Path(curv_root_dir).resolve()) if isinstance(curv_root_dir, (FsPathType, Path)) else curv_root_dir
    if build_dir is not None:
        kwargs['build_dir'] = str(Path(build_dir).resolve()) if isinstance(build_dir, (FsPathType, Path)) else build_dir
    if profile is not None:
        kwargs['profile'] = profile.stem if isinstance(profile, (FsPathType, Path)) else profile
    if board is not None:
        kwargs['board'] = board.stem if isinstance(board, (FsPathType, Path)) else board
    if device is not None:
        kwargs['device'] = device.stem if isinstance(device, (FsPathType, Path)) else device
    if merged_toml_path is not None:
        kwargs['merged_toml'] = merged_toml_path if isinstance(merged_toml_path, (FsPathType, Path)) else merged_toml_path
    ctx.obj['CurvPaths'].update_and_refresh(**kwargs)

@click.group(
    cls=CurvcfgHelpFormatterGroup,
    context_settings=CONTEXT_SETTINGS,
    epilog=None,
    invoke_without_command=True,
)
@version_opt()
@click.option(
    "--curv-root-dir",
    "curv_root_dir",
    metavar="<curv-root-dir>",
    show_default=True, # default comes from default_map["curv_root_dir"] from early args
    help=(
        "Overrides CURV_ROOT_DIR found from the environment or git-rev-parse."
    ),
    envvar="CURV_ROOT_DIR",
    shell_complete=shell_complete_curv_root_dir,
    is_eager=True,
)
@kind_opts(default_kind=Kind.SOC)
@verbosity_opts(include_verbose=True)
@click.pass_context
def cli(
    ctx: click.Context,
    curv_root_dir: Optional[str],
    kind: Kind,
    verbose: int,
) -> None:
    """curvcfg command line interface"""
    # no-op if ctx.obj is already a dict created by preparse() and passed in by main()
    ctx.ensure_object(dict)
    # Only override if not already set by preparse()
    # Effective value resolution *inside* Click:
    #   1. CLI option (--curv_root_dir)
    #   2. envvar CURV_ROOT_DIR
    #   3. default_map["curv_root_dir"] (if provided)
    #   4. parameter default (if defined)
    ctx.obj.setdefault("curv_root_dir", curv_root_dir)
    update_curvpaths(
        ctx=ctx, 
        curv_root_dir=curv_root_dir, 
    )
    ctx.obj["verbosity"] = max(ctx.obj.get("verbosity", 0), min(verbose, 3))
    
@cli.command(
    name="merge",
    cls=CurvcfgHelpFormatterCommand,
    context_settings=CONTEXT_SETTINGS,
    short_help="Merge TOML files",
    help=f"Merges one or more TOML files to create a merged TOML output file. Each TOML file listed may add to or override settings in earlier TOML files, with the last taking the highest precedence."
)
@profile_file_opt(required=True)
@schema_file_opt(required=True)
@overlay_opts_for_paths_list(default=None)
@build_dir_opt(must_exist=False, help="Base build directory; outputs written under this directory")
@merged_toml_output_opt(name="merged_file")
@output_dep_opt(must_exist=False)
@board_device_opts(default_board_name="ulx3s", default_device_name="85f")
@verbosity_opts(include_verbose=True)
@click.pass_context
def merge(
    ctx: click.Context,
    profile_file: FsPathType,
    schema_file_list: list[FsPathType],
    overlay_path_list: list[FsPathType],
    build_dir: FsPathType,
    merged_file: FsPathType,
    dep_file: FsPathType,
    board_dir: FsPathType,
    device_toml: FsPathType,
    verbose: int,
) -> None:
    update_curvpaths(
        ctx=ctx, 
        build_dir=build_dir, 
        profile=profile_file, 
        board=board_dir,
        device=device_toml,
    )

    merge_args: CurvCliArgs = {
        "curv_root_dir": ctx.obj.get("curv_root_dir"),
        "profile_file": profile_file,
        "schema_file_list": schema_file_list,
        "overlay_path_list": overlay_path_list,
        "build_dir": build_dir,
        "merged_file": merged_file,
        "dep_file": dep_file,
        "board_dir": board_dir,
        "device_toml": device_toml,
        "verbosity": max(ctx.obj["verbosity"], min(verbose, 2)),
    }

    if int(merge_args.get("verbosity", 0) or 0) >= 3:
        display_tool_settings(ctx)
        display_args_table(merge_args, "merge")
    rc = _merge_impl(merge_args, ctx.obj)
    raise SystemExit(rc)


@cli.command(
    cls=CurvcfgHelpFormatterCommand,
    context_settings=CONTEXT_SETTINGS,
    epilog=None,
)
@build_dir_opt(must_exist=True, help="Base build directory; outputs written to this directory.  Also used to locate <merged-toml> by default, unless --merged-toml overrides with a specific path.")
@merged_toml_input_opt(name="merged_file")
@schema_file_opt(required=True)
@board_device_opts(default_board_name="ulx3s", default_device_name="85f")
@verbosity_opts(include_verbose=True)
@click.pass_context
def generate(
    ctx: click.Context, 
    build_dir: FsPathType, 
    merged_file: FsPathType, 
    schema_file_list: list[FsPathType], 
    board_dir: FsPathType,
    device_toml: FsPathType,
    verbose: int
) -> None:
    """Generate output files from a merged TOML and schema."""
    update_curvpaths(
        ctx=ctx, 
        build_dir=build_dir, 
        merged_toml_path=merged_file,
        board=board_dir,
        device=device_toml,
    )
    generate_args: CurvCliArgs = {
        "curv_root_dir": ctx.obj.get("curv_root_dir"),
        "build_dir": build_dir,
        "merged_file": merged_file,
        "schema_file_list": schema_file_list,
        "board_dir": board_dir,
        "device_toml": device_toml,
        "verbosity": max(ctx.obj["verbosity"], min(verbose, 2)),
    }
    if int(generate_args.get("verbosity", 0) or 0) >= 3:
        display_args_table(generate_args, "generate")
    rc = _generate_impl(generate_args, ctx.obj)
    raise SystemExit(rc)



@cli.command(name="completions", cls=CurvcfgHelpFormatterCommand, context_settings=CONTEXT_SETTINGS)
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
    _exit_code = _completions_impl(completions_args, ctx.obj, prog_name)
    raise SystemExit(_exit_code)



@cli.group(name="show", 
    cls=CurvcfgHelpFormatterGroup, 
    context_settings=CONTEXT_SETTINGS, 
    help="Show active build configuration values and related information",
    epilog=None,
)
@verbosity_opts(include_verbose=True)
@click.pass_context
def show(ctx: click.Context, verbose: int) -> None:
    """Show active build configuration values and related information"""
    # ctx.obj["verbosity"] = max(min(verbose, 3), ctx.obj.get("verbosity", 0))

@show.command(name="vars", context_settings=CONTEXT_SETTINGS,
    short_help="Show active configuration variables",
    help="Show active configuration variables that apply in the current build environment based on the <build-dir>/config/merged.toml file. If such a file does not exist, then nothing is shown.")
@build_dir_opt(must_exist=True, help=(
    f"Base build directory; used to locate <merged-toml> "
    "by default, unless --merged-toml overrides with a specific "
    "path."
))
@profile_file_opt(required=True)
@overlay_opts_for_paths_list(default=None)
@merged_toml_input_opt(name="merged_file")
@board_device_opts(default_board_name="ulx3s", default_device_name="85f")
@verbosity_opts(include_verbose=True)
@click.pass_context
def show_active_variables(
    ctx: click.Context, 
    build_dir: FsPathType, 
    profile_file: FsPathType, 
    overlay_path_list: list[FsPathType], 
    merged_file: FsPathType, 
    board_dir: FsPathType,
    device_toml: FsPathType,
    verbose: int
) -> None:
    update_curvpaths(
        ctx=ctx, 
        build_dir=build_dir, 
        profile=profile_file, 
        merged_toml_path=merged_file,
        board=board_dir,
        device=device_toml,
    )

    show_args: CurvCliArgs = {
        "curv_root_dir": ctx.obj.get("curv_root_dir"),
        "build_dir": build_dir,
        "profile_file": profile_file,
        "overlay_path_list": overlay_path_list,
        "merged_file": merged_file,
        "board_dir": board_dir,
        "device_toml": device_toml,
        "verbosity": max(ctx.obj["verbosity"], min(verbose, 3)),
    }
    
    if int(show_args.get("verbosity", 0) or 0) >= 3:
        display_tool_settings(ctx)
        display_args_table(show_args, "show")
    rc = _show_active_variables_impl(show_args, ctx.obj)
    raise SystemExit(rc)

# @show.command(
#     cls=CurvcfgHelpFormatterCommand,
#     context_settings=CONTEXT_SETTINGS,
#     name="overlays", 
#     short_help=f"Shows the hierarchy of base config + overlays",
#     help=f"Shows the hierarchy of base config + overlays that generate the {DEFAULT_MERGED_TOML_NAME} in the current build environment")
# @profile_file_opt(required=True)
# @overlay_opts_for_paths_list(default=None)
# @verbosity_opts(include_verbose=True)
# @click.pass_context
# def show_overlays(
#     ctx: click.Context, 
#     profile_file: FsPathType,
#     overlay_path_list: list[FsPathType],
#     verbose: int,
# ) -> None:
#     show_args: CurvCliArgs = {
#         "curv_root_dir": ctx.obj.get("curv_root_dir"),
#         "profile_file": profile_file,
#         "overlay_path_list": overlay_path_list,
#         "verbosity": max(ctx.obj["verbosity"], min(verbose, 3)),
#     }
#     if int(show_args.get("verbosity", 0) or 0) >= 3:
#         display_args_table(show_args, "show")
#     rc = _show_overlays_impl(show_args, ctx.obj)
#     raise SystemExit(rc)

@show.command(name="profiles", cls=CurvcfgHelpFormatterCommand, context_settings=CONTEXT_SETTINGS,
    short_help="Show available base configurations (profiles)",
    help="Show available base configurations in $CURV_ROOT_DIR/config/profiles directory",
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
    rc = _show_profiles_impl(show_args, ctx.obj)
    raise SystemExit(rc)

@show.command(name="curvpaths", 
    cls=CurvcfgHelpFormatterCommand, 
    context_settings=CONTEXT_SETTINGS,
    short_help="Show interpolated paths read",
    help="Show the interpolatedpaths read from the path_raw.env file",
)
@build_dir_opt(must_exist=False)
@board_device_opts(default_board_name="ulx3s", default_device_name="85f")
@verbosity_opts(include_verbose=True)
@click.pass_context
def show_curvpaths(
    ctx: click.Context, 
    build_dir: FsPathType, 
    board_dir: FsPathType,
    device_toml: FsPathType,
    verbose: int
) -> None:
    """Show interpolated paths read from the path_raw.env file"""
    update_curvpaths(
        ctx=ctx, 
        build_dir=build_dir, 
        board=board_dir,
        device=device_toml,
    )
    show_args: CurvCliArgs = {
        "curv_root_dir": ctx.obj.get("curv_root_dir"),
        "build_dir": build_dir,
        "board_dir": board_dir,
        "device_toml": device_toml,
        "verbosity": max(ctx.obj["verbosity"], min(verbose, 2)),
    }
    if int(show_args.get("verbosity", 0) or 0) >= 3:
        display_args_table(show_args, "show curvpaths")
    
    # show the curvpaths
    try:
        display_curvpaths(ctx.obj["CurvPaths"])
    except Exception as e:
        console.print(f"[red]error:[/red] {e}")
        raise SystemExit(1)
    raise SystemExit(0)

# entry point
def main(argv: Optional[list[str]] = None) -> int:
    """
    This is the curvcfg CLI program's true entry point.
    """
    import click
    install(show_locals=True, word_wrap=True, width=get_console_width(), suppress=[click])

    def _process_early_args(argv: Optional[list[str]] = sys.argv[1:]) -> list[EarlyArg]:
        from curvpyutils.file_utils.repo_utils import get_git_repo_root
        from curvtools.cli.curvcfg.lib.curvpaths import get_curv_root_dir_from_repo_root
        try:
            repo_fallback_curv_root_dir = get_curv_root_dir_from_repo_root(get_git_repo_root())
        except Exception:
            repo_fallback_curv_root_dir = None
        early_curv_root_dir = EarlyArg(
            ["--curv-root-dir"], 
            env_var_fallback="CURV_ROOT_DIR", 
            default_value_fallback=repo_fallback_curv_root_dir
        )
        preparse([early_curv_root_dir], argv=argv)
        return [early_curv_root_dir]
    
    try:
        [early_curv_root_dir] = _process_early_args() # list of one EarlyArg object
        ctx_obj: dict = {}
        default_map: dict = {}
        if early_curv_root_dir.valid:
            set_epilog_fn(early_curv_root_dir.value, early_curv_root_dir.source)
            ctx_obj["curv_root_dir"] = early_curv_root_dir.value
            ctx_obj["CurvPaths"] = get_curv_paths(early_curv_root_dir.value)
            default_map["curv_root_dir"] = early_curv_root_dir.value
        cli.main(
            args=argv, 
            standalone_mode=True, 
            obj=ctx_obj,
            default_map=default_map,
        )
    except SystemExit as e:
        return int(e.code)
        raise e
    return 0

# never executes
if __name__ == "__main__":
    sys.exit(main())
