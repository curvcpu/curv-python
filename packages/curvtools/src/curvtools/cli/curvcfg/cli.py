from __future__ import annotations
import click
from rich.traceback import install
from rich.console import Console
from curvpyutils.shellutils import get_console_width
from pathlib import Path
from curvtools.cli.curvcfg.cli_helpers.help_formatter import (
    CurvcfgHelpFormatterGroup, 
    CurvcfgHelpFormatterCommand, 
    set_epilog_fn,
)
from curvtools.cli.curvcfg.cli_helpers.opts.curv_root_dir_opt import shell_complete_curv_root_dir
from curvtools.cli.curvcfg.cli_helpers.opts.build_dir_opts import shell_complete_build_dir
from curvtools.cli.curvcfg.cli_helpers.opts.version_opt import version_opt
from curvtools.cli.curvcfg.lib.curv_paths.curvcontext import CurvContext
from curvtools.cli.curvcfg.lib.curv_paths import try_get_curvrootdir_git_fallback
from typing import Optional
from curvtools.cli.curvcfg.cli_helpers.paramtypes import ( 
    ProfileResolvable, 
    DeviceResolvable, 
    BoardResolvable, 
    InputMergedTomlResolvable,
    OutputMergedTomlResolvable,
    profile_type, 
    device_type, 
    board_type,
    input_merged_toml_type,
    output_merged_toml_type,
    schema_file_type,
)
from curvtools.cli.curvcfg.lib.util.draw_tables import ( 
    display_curvpaths,
    display_args_table,
    display_merged_toml_table,
    display_dep_file_contents,
    display_tool_settings,
)
from curvtools.cli.curvcfg.cli_helpers.opts import (
    verbosity_opts, 
    FsPathType
)
from curvtools.cli.curvcfg.show import (
    show_profiles_impl,
    show_active_variables_impl,
)
from curvtools.cli.curvcfg.board import (
    merge_board_impl,
)
import sys

CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
}

################################################################################################################################################################################################################
#
# Command line interface
#
################################################################################################################################################################################################################
# Intended usage patterns:
#   curvcfg --curv-root-dir=... --build-dir=... [-vvv] board                               merge     --board=... --device=...                                      --schema=... --schema=... --merged_board_toml_out=... --dep-file-out=...
#   curvcfg --curv-root-dir=... --build-dir=... [-vvv] board                               generate  --merged_board_toml_in=...
#   curvcfg --curv-root-dir=... --build-dir=... [-vvv] tb                                  merge     --profile=...               --overlay=... --overlay=... [...] --schema=... --schema=... --merged-toml-out=...       --dep-file-out=...
#   curvcfg --curv-root-dir=... --build-dir=... [-vvv] tb                                  generate  --merged-toml-in=...
#   curvcfg --curv-root-dir=... --build-dir=... [-vvv] soc                                 merge     --profile=...               --overlay=... --overlay=... [...] --schema=... --schema=... --merged-toml-out=...       --dep-file-out=...
#   curvcfg --curv-root-dir=... --build-dir=... [-vvv] soc                                 generate  --merged-toml-in=...
#   curvcfg --curv-root-dir=... --build-dir=... [-vvv] show                                profiles
#   curvcfg --curv-root-dir=... --build-dir=... [-vvv] show                                curvpaths [--board=...] [--device=...]
#   curvcfg --curv-root-dir=... --build-dir=... [-vvv] show                                vars      --merged-toml-in=... (can be merged.toml or merged_board.toml)
################################################################################################################################################################################################################

@click.group(
    context_settings=CONTEXT_SETTINGS,
)
@click.option(
    "--curv-root-dir",
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True, exists=True),
    required=False,
    help="CurvCPU project root directory; defaults to CURV_ROOT_DIR environment variable with fallback to current repo root if you're in a git repo with 'curvcpu/curv' in its .git/config file.",
    envvar="CURV_ROOT_DIR",
    shell_complete=shell_complete_curv_root_dir,
)
@click.option(
    "--build-dir",
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True, exists=False),
    required=False,
    help="Build output directory. Defaults to CURV_BUILD_DIR environment variable if set, otherwise 'build/' relative to the current working directory.",
    envvar="CURV_BUILD_DIR",
    shell_complete=shell_complete_build_dir,
)
@verbosity_opts(include_verbose=True)
@version_opt()
@click.pass_context
def curvcfg(ctx: click.Context, curv_root_dir: Optional[str], build_dir: Optional[str], verbosity: int):
    """
    Curv configuration tool
    """
    curvctx = ctx.ensure_object(CurvContext)
    curvctx.curv_root_dir = curv_root_dir
    curvctx.build_dir = build_dir
    curvctx.ctx = ctx
    set_epilog_fn_arg_list = []
    if curv_root_dir is not None:
        # Where did curv_root_dir come from?
        # src is one of:
        #   ParameterSource.COMMANDLINE
        #   ParameterSource.ENVIRONMENT
        #   ParameterSource.DEFAULT_MAP
        #   ParameterSource.DEFAULT (param default)
        #   ParameterSource.NONE (if truly unset)
        #   ParameterSource.PROMPT (if prompted)
        #   None (if truly unset)
        src = ctx.get_parameter_source("curv_root_dir")
        p = Path(curv_root_dir)
        if p.exists() and p.is_dir():
            set_epilog_fn_arg_list.append(("CURV_ROOT_DIR", curv_root_dir, src))
    if build_dir is not None:
        src = ctx.get_parameter_source("build_dir")
        p = Path(build_dir)
        set_epilog_fn_arg_list.append(("CURV_BUILD_DIR", build_dir, src))
    if len(set_epilog_fn_arg_list) > 0:
        set_epilog_fn(set_epilog_fn_arg_list)
    curvctx.args["verbosity"] = verbosity

########################################################
#
# Subcommand groups
#
########################################################

#######################
# tb subcommand group #
#######################

@curvcfg.group(
    cls=CurvcfgHelpFormatterGroup, 
    context_settings=CONTEXT_SETTINGS,
)
@click.pass_obj
def tb(curvctx: CurvContext):
    """Testbench-related commands"""
    # nothing else; we’ll call curvctx.make_paths() in subcommands
    pass

########################
# soc subcommand group #
########################

@curvcfg.group(
    cls=CurvcfgHelpFormatterGroup, 
    context_settings=CONTEXT_SETTINGS,
)
@click.pass_context
def soc(ctx: click.Context):
    """SoC-related commands"""
    pass

##########################
# board subcommand group #
##########################

@curvcfg.group(
    cls=CurvcfgHelpFormatterGroup, 
    context_settings=CONTEXT_SETTINGS,
)
@click.pass_context
def board(ctx: click.Context):
    """SoC-related commands"""
    pass

#########################
# show subcommand group #
#########################

@curvcfg.group(
    cls=CurvcfgHelpFormatterGroup, 
    context_settings=CONTEXT_SETTINGS,
)
@click.pass_context
def show(ctx: click.Context):
    """Show subcommands"""
    pass

########################################################
#
# Subcommands
#
########################################################

##########################
# board merge subcommand #
##########################

@board.command(name="merge")
@click.option(
    "--board",
    "board_name",
    type=board_type,
    required=True,
    help="Board name or path to board directory or path to board TOML file",
    expose_value=True,
)
@click.option(
    "--device",
    "device_name",
    type=device_type,
    required=True,
    help="Device name or path to device TOML file",
    expose_value=True,
)
@click.option(
    "--schema",
    "schemas",
    type=schema_file_type,
    multiple=True,
    required=True,
    help="Schema TOML file(s); may be given multiple times; order matters.",
)
@click.option(
    "--merged-board-toml-out",
    "merged_toml_out",
    type=output_merged_toml_type,
    required=True,
    help="Path to merged board config TOML output file",
)
@click.option(
    "--dep-file-out",
    type=click.Path(exists=False, dir_okay=False, resolve_path=True),
    required=True,
    help="Path to Makefile dependency file output file for merged board configuration",
)
@click.pass_obj
def merge_board(curvctx: CurvContext, board_name: BoardResolvable, device_name: DeviceResolvable, schemas: list[FsPathType], merged_toml_out: OutputMergedTomlResolvable, dep_file_out: click.Path):
    """
    Merge schemas, board.toml, and <device-name>.toml for hardware configuration and write merged_board.toml + board.mk.d
    """
    merged_board_toml_out_path = merged_toml_out.resolve(curvctx.curvpaths).path
    curvctx.board = board_name.resolve(curvctx.curvpaths).name
    curvctx.device = device_name.resolve(curvctx.curvpaths).name
    curv_paths = curvctx.make_paths()

    merge_board_impl(curvctx, board_name, device_name, schemas, merged_board_toml_out_path, dep_file_out)



############################
# soc generate subcommand  #
############################

@board.command(name="generate")
@click.option(
    "--merged-board-toml-in",
    type=input_merged_toml_type,
    required=True,
    help="Path to merged board config TOML input file",
)
@click.pass_obj
def generate_board(curvctx: CurvContext, merged_board_toml_in: InputMergedTomlResolvable):
    """
    Generate board configuration files from merged_board.toml
    """
    merged_board_toml_in_path = merged_board_toml_in.resolve(curvctx.curvpaths).path
    verbosity = int(curvctx.args.get("verbosity", 0))
    curv_paths = curvctx.make_paths()

    if verbosity >= 2:
        show_args: dict[str, Any] = {
            "curv_root_dir": curv_paths.curv_root_dir,
            "build_dir": curvctx.build_dir,
            "merged_board_toml_in": merged_board_toml_in_path,
            "verbosity": verbosity,
        }
        display_tool_settings(curvctx)
        display_args_table(show_args, "board generate")

    pass

########################
# soc merge subcommand #
########################

@soc.command(name="merge")
@click.option(
    "--profile",
    type=profile_type,
    required=True,
    help="Profile name or path to TOML profile.",
)
@click.option(
    "--schema",
    "schemas",
    type=schema_file_type,
    multiple=True,
    required=True,
    help="Schema TOML file(s); may be given multiple times; order matters.",
)
@click.option(
    "--overlay",
    "overlays",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    multiple=True,
    help="Overlay TOML file(s); may be given multiple times; later overrides earlier.",
)
@click.option(
    "--merged-toml-out",
    type=output_merged_toml_type,
    required=True,
    help="Path to merged config TOML output file",
)
@click.option(
    "--dep-file-out",
    type=click.Path(exists=False, dir_okay=False, resolve_path=True),
    required=True,
    help="Path to Makefile dependency file output file",
)
@click.pass_obj
def merge_soc(curvctx: CurvContext, profile: ProfileResolvable, schemas: list[FsPathType], overlays: list[click.Path], merged_toml_out: OutputMergedTomlResolvable, dep_file_out: click.Path):
    """
    Merge schemas/overlays for SoC configuration and write merged.toml + config.mk.d
    """
    curvctx.profile = profile.resolve(curvctx.curvpaths)
    curv_paths = curvctx.make_paths()

    print("--------------------------------")
    print(f"curv_paths = {str(curv_paths)}")


    # # merge overlays
    # merged_overlay = merge_overlays(overlays)
    #
    # # read schemas
    # schema_objs = [MergedToml.from_file(p) for p in schemas]
    #
    # # hypothetical API
    # merged = merge_everything(
    #     profile=profile,
    #     schemas=schema_objs,
    #     overlay=merged_overlay,
    #     curv_paths=curv_paths,
    # )
    # same merging logic, but presumably different target paths/contents
    pass


############################
# soc generate subcommand  #
############################

@soc.command(name="generate")
@click.option(
    "--merged-toml-in",
    type=input_merged_toml_type,
    required=True,
    help="Path to merged config TOML input file",
)
@click.pass_obj
def generate_soc(curvctx: CurvContext, merged_toml_in: InputMergedTomlResolvable):
    """
    Generate SoC configuration files from merged.toml
    """
    merged_toml_in_path = merged_toml_in.resolve(curvctx.curvpaths).path
    verbosity = int(curvctx.args.get("verbosity", 0))
    curv_paths = curvctx.make_paths()

    if verbosity >= 2:
        show_args: dict[str, Any] = {
            "curv_root_dir": curv_paths.curv_root_dir,
            "build_dir": curvctx.build_dir,
            "merged_toml_in": merged_toml_in_path,
            "verbosity": verbosity,
        }
        display_tool_settings(curvctx)
        display_args_table(show_args, "soc generate")

    #
    # TODO
    # 
    pass

########################
# tb merge subcommand #
########################

@tb.command(name="merge")
@click.option(
    "--profile",
    type=profile_type,  # or just str and resolve later
    required=True,
    help="Profile name or path to TOML profile.",
)
@click.option(
    "--schema",
    "schemas",
    type=schema_file_type,
    multiple=True,
    required=True,
    help="Schema TOML file(s); may be given multiple times; order matters.",
)
@click.option(
    "--overlay",
    "overlays",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    multiple=True,
    help="Overlay TOML file(s); may be given multiple times; later overrides earlier.",
)
@click.pass_obj
def merge_tb(curvctx: CurvContext, profile: ProfileResolvable, schemas: list[FsPathType], overlays: list[click.Path]):
    """
    Merge schemas/overlays for TB configuration and write merged.toml + config.mk.d
    """
    curvctx.profile = profile.resolve(curvctx.curvpaths)
    curv_paths = curvctx.make_paths()

    # # merge overlays
    # merged_overlay = merge_overlays(overlays)
    #
    # # read schemas
    # schema_objs = [MergedToml.from_file(p) for p in schemas]
    #
    # # hypothetical API
    # merged = merge_everything(
    #     profile=profile,
    #     schemas=schema_objs,
    #     overlay=merged_overlay,
    #     curv_paths=curv_paths,
    # )
    # merged_path = curv_paths.tb_merged_toml_path()
    # mkd_path    = curv_paths.tb_config_mkd_path()
    # merged.write(merged_path)
    # write_config_mk_d(merged, mkd_path)

##########################
# tb generate subcommand #
##########################

@tb.command(name="generate")
@click.option(
    "--merged-toml-in",
    type=input_merged_toml_type,
    required=True,
    help="Path to merged config TOML input file",
)
@click.pass_obj
def generate_tb(curvctx: CurvContext, merged_toml_in: InputMergedTomlResolvable):
    """
    Generate TB configuration files from merged.toml
    """
    merged_toml_in_path = merged_toml_in.resolve(curvctx.curvpaths).path
    verbosity = int(curvctx.args.get("verbosity", 0))
    curv_paths = curvctx.make_paths()

    if verbosity >= 2:
        show_args: dict[str, Any] = {
            "curv_root_dir": curv_paths.curv_root_dir,
            "build_dir": curvctx.build_dir,
            "merged_toml_in": merged_toml_in_path,
            "verbosity": verbosity,
        }
        display_tool_settings(curvctx)
        display_args_table(show_args, "tb generate")

    #
    # TODO: implement
    # 

# ########################
# # show vars subcommand #
# ########################

@show.command(
    name="vars", 
    cls=CurvcfgHelpFormatterCommand, 
    context_settings=CONTEXT_SETTINGS,
    short_help="Show active configuration variables",
    help="Show active configuration variables that apply in the current build environment based on the build directory's merged.toml file. If such a file does not exist, then nothing is shown.")
@click.option(
    "--merged-toml-in",
    type=input_merged_toml_type,
    required=True,
    help="Path to merged config TOML input file",
)
@click.pass_obj
def show_active_variables(
    curvctx: CurvContext,
    merged_toml_in: InputMergedTomlResolvable
) -> None:
    merged_toml_in_path = merged_toml_in.resolve(curvctx.curvpaths).path
    curv_paths = curvctx.make_paths()
    verbosity = int(curvctx.args.get("verbosity", 0))

    if verbosity >= 2:
        show_args: dict[str, Any] = {
            "curv_root_dir": curv_paths.curv_root_dir,
            "build_dir": curvctx.build_dir,
            "merged_toml_in": merged_toml_in_path,
            "verbosity": verbosity,
        }
        display_tool_settings(curvctx)
        display_args_table(show_args, "show")
    
    rc = show_active_variables_impl(merged_toml_in_path, curv_paths, verbosity)
    raise SystemExit(rc)

############################
# show profiles subcommand #
############################

@show.command(
    name="profiles", 
    cls=CurvcfgHelpFormatterCommand, 
    context_settings=CONTEXT_SETTINGS,
    short_help="Show available profiles",
)
@click.pass_obj
def show_profiles(curvctx: CurvContext) -> None:
    """Show available profiles (base configurations)"""

    # curvctx = ctx.find_object(CurvContext)

    curv_paths = curvctx.make_paths()

    if int(curvctx.args.get("verbosity", 0)) >= 2:
        board_toml = curv_paths["CURV_CONFIG_BOARD_TOML_PATH"]
        board_name = curv_paths["CURV_CONFIG_BOARD_TOML_PATH"].to_path().parent.name
        device_toml = curv_paths["CURV_CONFIG_DEVICE_TOML_PATH"]
        device_name = curv_paths["CURV_CONFIG_DEVICE_TOML_PATH"].to_path().stem
        show_args: dict[str, Any] = {
            "curv_root_dir": curvctx.curv_root_dir,
            "build_dir": curvctx.build_dir,
            "board_toml": board_toml if board_toml.is_fully_resolved() and board_toml.to_path().exists() else None,
            "board_name": board_name if board_name != "$(BOARD)" else None,
            "device_toml": device_toml if device_toml.is_fully_resolved() and device_toml.to_path().exists() else None,
            "device_name": device_name if device_name != "$(DEVICE)" else None,
            "verbosity": curvctx.args.get("verbosity", 0),
        }
        display_args_table(show_args, "show")

    rc = show_profiles_impl(curv_paths)
    raise SystemExit(rc)

#############################
# show curvpaths subcommand #
#############################

@show.command(name="curvpaths", 
    cls=CurvcfgHelpFormatterCommand, 
    context_settings=CONTEXT_SETTINGS,
    short_help="Show interpolated paths",
)
@click.option(
    "--board",
    "board_name",
    type=board_type,
    required=False,
    help="Board name or path to board directory or path to board TOML file",
    expose_value=False,
)
@click.option(
    "--device",
    "device_name",
    type=device_type,
    required=False,
    help="Device name or path to device TOML file",
    expose_value=False,
)
@click.pass_obj
def show_curvpaths(
    curvctx: CurvContext
) -> None:
    """Show the interpolatedpaths read from the path_raw.env file"""

    curv_paths = curvctx.make_paths()

    if int(curvctx.args.get("verbosity", 0)) >= 2:
        board_toml = curv_paths["CURV_CONFIG_BOARD_TOML_PATH"]
        board_name = curv_paths["CURV_CONFIG_BOARD_TOML_PATH"].to_path().parent.name
        device_toml = curv_paths["CURV_CONFIG_DEVICE_TOML_PATH"]
        device_name = curv_paths["CURV_CONFIG_DEVICE_TOML_PATH"].to_path().stem
        show_args: dict[str, Any] = {
            "curv_root_dir": curvctx.curv_root_dir,
            "build_dir": curvctx.build_dir,
            "board_toml": board_toml if board_toml.is_fully_resolved() and board_toml.to_path().exists() else None,
            "board_name": board_name if board_name != "$(BOARD)" else None,
            "device_toml": device_toml if device_toml.is_fully_resolved() and device_toml.to_path().exists() else None,
            "device_name": device_name if device_name != "$(DEVICE)" else None,
            "verbosity": curvctx.args.get("verbosity", 0),
        }
        display_args_table(show_args, "show curvpaths")
    
    # show the curvpaths
    try:
        display_curvpaths(curv_paths)
    except Exception as e:
        console.print(f"[red]error:[/red] {e}")
        raise SystemExit(1)
    raise SystemExit(0)


def main(argv: Optional[list[str]] = None) -> int:
    """
    This is the curvcfg CLI program's true entry point.
    """
    import click
    install(show_locals=True, word_wrap=True, width=get_console_width(), suppress=[click])
    try:
        ctx_obj: dict = {}
        default_map: dict = {}
        default_map["curv_root_dir"] = str(try_get_curvrootdir_git_fallback() or "")
        default_map["build_dir"] = str(Path.cwd() / "build")
        default_map["verbosity"] = 0
        curvcfg.main(
            args=argv, 
            standalone_mode=True, 
            obj=ctx_obj,
            default_map=default_map,
        )
    except SystemExit as e:
        return int(e.code)
    return 0

# never executes
if __name__ == "__main__":
    sys.exit(main())
