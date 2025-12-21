from __future__ import annotations
import click
from rich.traceback import install
from rich.console import Console
from curvpyutils.shellutils import get_console_width
from pathlib import Path
from curvtools.cli.curvcfg.cli_helpers.help_formatter import (
    CurvcfgHelpFormatterGroup, 
    CurvcfgHelpFormatterCommand, 
    update_epilog_env_vars,
)
from curvpyutils.cli_util import preparse, EarlyArg
from curvtools.cli.curvcfg.lib.curv_paths import get_curv_paths
from curvtools.cli.curvcfg.cli_helpers.opts.curv_root_dir_opt import shell_complete_curv_root_dir
from curvtools.cli.curvcfg.cli_helpers.opts.build_dir_opts import shell_complete_build_dir
from curvtools.cli.curvcfg.cli_helpers.opts.version_opt import version_opt
from curvtools.cli.curvcfg.lib.curv_paths.curvcontext import CurvContext
from curvtools.cli.curvcfg.lib.curv_paths import try_get_curvrootdir_git_fallback
from typing import Any, Optional
from curvtools.cli.curvcfg.cli_helpers.paramtypes import ( 
    ProfileResolvable, 
    DeviceResolvable, 
    BoardResolvable, 
    InputMergedTomlResolvable,
    profile_type, 
    device_type, 
    board_type,
    input_merged_board_toml_type,
    output_merged_board_toml_type,
    input_merged_config_toml_type,
    output_merged_config_toml_type,
    input_merged_toml_type,
    schema_file_type,
)
from curvtools.cli.curvcfg.lib.util.draw_tables import ( 
    display_curvpaths,
    display_args_table,
    display_merged_toml_table,
    display_dep_file_contents,
    display_tool_settings,
    display_default_map,
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
from curvtools.cli.curvcfg.generate import (
    generate_board_artifacts_impl,
    generate_config_artifacts_impl,
)
from curvtools.cli.curvcfg.merge import merged_cfgvars_impl
from curvtools.cli.curvcfg.cli_helpers.default_map import DefaultMapArgs
import sys
from curvtools.cli.curvcfg.lib.globals.constants import (
    REL_BUILD_DIR_DEFAULT,
)

CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
}

_TEMPLATE_SUFFIX_TO_KEY = {
    ".sv.jinja2": "svpkg_template",
    ".svh.jinja2": "svh_template",
    ".mk.jinja2": "mk_template",
    ".env.jinja2": "env_template",
}


def _bucket_templates_by_suffix(
    templates: tuple[str, ...],
    option_name: str = "--template",
) -> dict[str, Optional[Path]]:
    """
    Ensure each template ends with an allowed suffix and bucket by type.
    """
    buckets: dict[str, Optional[Path]] = {
        value: None for value in _TEMPLATE_SUFFIX_TO_KEY.values()
    }

    for template in templates:
        template_path = Path(template)
        matched_suffix = next(
            (suffix for suffix in _TEMPLATE_SUFFIX_TO_KEY if template_path.name.endswith(suffix)),
            None,
        )
        if matched_suffix is None:
            allowed_suffixes = ", ".join(sorted(_TEMPLATE_SUFFIX_TO_KEY.keys()))
            raise click.BadParameter(
                f"Template '{template_path}' must end with one of: {allowed_suffixes}",
                param_hint=option_name,
            )

        key = _TEMPLATE_SUFFIX_TO_KEY[matched_suffix]
        if buckets[key] is not None:
            raise click.BadParameter(
                f"Multiple templates supplied for '*{matched_suffix}'",
                param_hint=option_name,
            )
        buckets[key] = template_path

    return buckets


################################################################################################################################################################################################################
#
# Command line interface
#
################################################################################################################################################################################################################
# Intended usage patterns:
#   curvcfg --curv-root-dir=... --build-dir=... [-vvv] board                               merge     --board=... --device=...                                      --schema=... --schema=... --merged-board-toml-out=... --dep-file-out=...
#     👆 produces generated/{config/intermediates/merged_board.toml, make/board.mk.d}
#   curvcfg --curv-root-dir=... --build-dir=... [-vvv] board                               generate  --merged_board_toml=...     [--template=[*.sv.jinja2|.svh.jinja2|.env.jinja2|.mk.jinja2]]
#     👆 generated/{make/board.mk, hdl/board.sv, hdl/board.svh}
#
#   curvcfg --curv-root-dir=... --build-dir=... [-vvv] cfgvars                             merge     [--tb] --profile=...        --overlay=... --overlay=... [...] --schema=... --schema=... --merged-config-toml-out=...                                --dep-file-out=...
#   curvcfg --curv-root-dir=... --build-dir=... [-vvv] cfgvars                             generate  --merged-config-toml-in=... [--template=[*.sv.jinja2|.svh.jinja2|.env.jinja2|.mk.jinja2]]
#
#   curvcfg --curv-root-dir=... --build-dir=... [-vvv] show                                profiles
#   curvcfg --curv-root-dir=... --build-dir=... [-vvv] show                                curvpaths [--profile=...] [--board=...] [--device=...]
#   curvcfg --curv-root-dir=... --build-dir=... [-vvv] show                                vars      --merged-toml-in=...
################################################################################################################################################################################################################

@click.group(
    cls=CurvcfgHelpFormatterGroup, 
    context_settings=CONTEXT_SETTINGS,
)
@click.option(
    "--curv-root-dir", '-R', 
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True, exists=True),
    required=False,
    help="CurvCPU project root directory; defaults to CURV_ROOT_DIR environment variable with fallback to current repo root if you're in a git repo with 'curvcpu/curv' in its .git/config file.",
    envvar="CURV_ROOT_DIR",
    shell_complete=shell_complete_curv_root_dir,
)
@click.option(
    "--build-dir", '-B',
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True, exists=False),
    required=False,
    help=f"Build output directory. Defaults to CURV_BUILD_DIR environment variable if set, otherwise '{REL_BUILD_DIR_DEFAULT}/' relative to the current working directory.",
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
            update_epilog_env_vars("CURV_ROOT_DIR", curv_root_dir, src)
    if build_dir is not None:
        src = ctx.get_parameter_source("build_dir")
        p = Path(build_dir)
        update_epilog_env_vars("CURV_BUILD_DIR", build_dir, src)
    curvctx.args["verbosity"] = verbosity
    default_map = ctx.default_map
    if verbosity >= 2:
        display_default_map(default_map)

########################################################
#
# Subcommand groups
#
########################################################

##########################
# board subcommand group #
##########################

@curvcfg.group(
    cls=CurvcfgHelpFormatterGroup, 
    context_settings=CONTEXT_SETTINGS,
)
@click.pass_context
def board(ctx: click.Context):
    """Board artifacts generation"""
    pass

##########################
# cfgvars subcommand group #
##########################

@curvcfg.group(
    cls=CurvcfgHelpFormatterGroup, 
    context_settings=CONTEXT_SETTINGS,
)
@click.pass_obj
def cfgvars(curvctx: CurvContext):
    """Configuration variables merging and artifact generation"""
    # nothing else; we’ll call curvctx.make_paths() in subcommands
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
    """Show information"""
    pass

########################################################
#
# Subcommands
#
########################################################

################################
# board merge subcommand       #
################################

@board.command(
    name="merge",
    cls=CurvcfgHelpFormatterCommand,
    context_settings=CONTEXT_SETTINGS,
)
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
    "--merged-board-toml",
    "merged_board_toml",
    type=output_merged_board_toml_type,
    required=True,
    help="Path to merged board config TOML output file",
)
@click.option(
    "--board-mk-dep",
    "board_mk_dep",
    type=click.Path(exists=False, dir_okay=False, resolve_path=True),
    required=True,
    help="Path to Makefile dependency file output file for merged board configuration",
)
@click.pass_obj
def merge_board(curvctx: CurvContext, board_name: BoardResolvable, device_name: DeviceResolvable, schemas: list[FsPathType], merged_board_toml: OutputMergedBoardTomlResolvable, board_mk_dep: click.Path):
    """
    Merge schemas, board.toml, and <device-name>.toml for hardware configuration and write merged_board.toml + board.mk.d
    """
    merged_board_toml_out_path = merged_board_toml.resolve(curvctx.curvpaths).path
    curvctx.board = board_name.resolve(curvctx.curvpaths).name
    curvctx.device = device_name.resolve(curvctx.curvpaths).name
    curv_paths = curvctx.make_paths()

    merge_board_impl(curvctx, board_name, device_name, schemas, merged_board_toml_out_path, board_mk_dep)



############################$$
# board generate subcommand  #
############################$$

@board.command(
    name="generate",
    cls=CurvcfgHelpFormatterCommand,
    context_settings=CONTEXT_SETTINGS,
)
@click.option(
    "--merged-board-toml",
    "merged_board_toml",
    type=input_merged_board_toml_type,
    required=True,
    help="Path to merged board config TOML input file",
)
@click.option(
    "--template",
    "templates",
    type=click.Path(file_okay=True, dir_okay=False, resolve_path=True, exists=True),
    multiple=True,
    required=False,
    help="Optional template override(s); may be given multiple times (.sv.jinja2, .svh.jinja2, .env.jinja2, .mk.jinja2).",
)
@click.pass_obj
def generate_board(curvctx: CurvContext, merged_board_toml: InputMergedBoardTomlResolvable, templates: tuple[str, ...]):
    """
    Generate board configuration artifacts from <merged_board_toml>
    """
    merged_board_toml_path = merged_board_toml.resolve(curvctx.curvpaths).path
    verbosity = int(curvctx.args.get("verbosity", 0))
    templates_by_suffix = _bucket_templates_by_suffix(templates)
    curv_paths = curvctx.make_paths()

    if verbosity >= 2:
        show_args: dict[str, Any] = {
            "curv_root_dir": curv_paths.curv_root_dir,
            "build_dir": curvctx.build_dir,
            "merged_board_toml": merged_board_toml_path,
            "svpkg_template": templates_by_suffix["svpkg_template"],
            "svh_template": templates_by_suffix["svh_template"],
            "mk_template": templates_by_suffix["mk_template"],
            "env_template": templates_by_suffix["env_template"],
            "verbosity": verbosity,
        }
        display_tool_settings(curvctx)
        display_args_table(show_args, "board generate")

    generate_board_artifacts_impl(
        curvctx,
        merged_board_toml_path,
        svpkg_template=templates_by_suffix["svpkg_template"],
        svh_template=templates_by_suffix["svh_template"],
        mk_template=templates_by_suffix["mk_template"],
        env_template=templates_by_suffix["env_template"],
    )

##############################
# cfgvars merge subcommand   #
##############################

@cfgvars.command(
    name="merge",
    cls=CurvcfgHelpFormatterCommand,
    context_settings=CONTEXT_SETTINGS,
)
@click.option(
    "--tb",
    "is_tb",
    is_flag=True,
    default=False,
    hidden=True,
    help="Treat configuration variables as testbench-oriented; defaults to deployment context.",
)
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
@click.option(
    "--merged-config-toml",
    "merged_config_toml",
    type=output_merged_config_toml_type,
    required=True,
    help="Path to merged config intermediate TOML output file",
)
@click.option(
    "--config-mk-dep",
    "config_mk_dep",
    type=click.Path(exists=False, dir_okay=False, resolve_path=True),
    required=True,
    help="Path to Makefile dependency file output file for merged config configuration",
)
@click.pass_obj
def merge_cfgvars(curvctx: CurvContext, is_tb: bool, profile: ProfileResolvable, schemas: list[FsPathType], overlays: list[click.Path], merged_config_toml: OutputMergedConfigTomlResolvable, config_mk_dep: click.Path):
    """
    Merge schemas/overlays for configuration variables and write merged_config.toml + config.mk.d
    """
    merged_config_toml_out_path = merged_config_toml.resolve(curvctx.curvpaths).path
    curvctx.profile = profile.resolve(curvctx.curvpaths).name
    curv_paths = curvctx.make_paths()
    merged_cfgvars_impl(curvctx, profile, schemas, overlays, merged_config_toml_out_path, config_mk_dep, is_tb=is_tb)

###############################
# cfgvars generate subcommand #
###############################

@cfgvars.command(
    name="generate",
    cls=CurvcfgHelpFormatterCommand,
    context_settings=CONTEXT_SETTINGS,
)
@click.option(
    "--merged-config-toml",
    "merged_config_toml",
    type=input_merged_config_toml_type,
    required=True,
    help="Path to merged config TOML input file",
)
@click.option(
    "--template",
    "templates",
    type=click.Path(file_okay=True, dir_okay=False, resolve_path=True, exists=True),
    multiple=True,
    required=False,
    help="Optional template override(s); may be given multiple times (.sv.jinja2, .svh.jinja2, .env.jinja2, .mk.jinja2).",
)
@click.pass_obj
def generate_cfgvars(curvctx: CurvContext, merged_config_toml: InputMergedConfigTomlResolvable, templates: tuple[str, ...]):
    """
    Generate configuration variable artifacts from merged_config.toml
    """
    merged_config_toml_path = merged_config_toml.resolve(curvctx.curvpaths).path
    verbosity = int(curvctx.args.get("verbosity", 0))
    templates_by_suffix = _bucket_templates_by_suffix(templates)
    curv_paths = curvctx.make_paths()

    if verbosity >= 2:
        show_args: dict[str, Any] = {
            "curv_root_dir": curv_paths.curv_root_dir,
            "build_dir": curvctx.build_dir,
            "merged_config_toml": merged_config_toml_path,
            "svpkg_template": templates_by_suffix["svpkg_template"],
            "svh_template": templates_by_suffix["svh_template"],
            "mk_template": templates_by_suffix["mk_template"],
            "env_template": templates_by_suffix["env_template"],
            "verbosity": verbosity,
        }
        display_tool_settings(curvctx)
        display_args_table(show_args, "cfgvars generate")

    generate_config_artifacts_impl(
        curvctx,
        merged_config_toml_path,
        svpkg_template=templates_by_suffix["svpkg_template"],
        svh_template=templates_by_suffix["svh_template"],
        mk_template=templates_by_suffix["mk_template"],
        env_template=templates_by_suffix["env_template"],
    )


########################
# show vars subcommand #
########################

@show.command(
    name="vars", 
    cls=CurvcfgHelpFormatterCommand, 
    context_settings=CONTEXT_SETTINGS,
    short_help="Show active configuration variables",
    help=f"Show active configuration variables from a <merged_toml> file in the build directory")
@click.option(
    "--merged-toml",
    "merged_toml",
    type=input_merged_toml_type,
    required=True,
    help="Path to merged config TOML input file",
)
@click.pass_obj
def show_active_variables(
    curvctx: CurvContext,
    merged_toml: InputMergedTomlResolvable
) -> None:
    merged_toml_in_path = merged_toml.resolve(curvctx.curvpaths).path
    curv_paths = curvctx.make_paths()
    verbosity = int(curvctx.args.get("verbosity", 0))

    if verbosity >= 2:
        show_args: dict[str, Any] = {
            "curv_root_dir": curv_paths.curv_root_dir,
            "build_dir": curvctx.build_dir,
            "merged_toml": merged_toml_in_path,
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
    "--profile",
    type=profile_type,
    required=True,
    help="Profile name or path to TOML profile.",
    expose_value=False,
)
@click.option(
    "--board",
    type=board_type,
    required=True,
    help="Board name or path to board directory or path to board TOML file",
    expose_value=False,
)
@click.option(
    "--device",
    type=device_type,
    required=True,
    help="Device name or path to device TOML file",
    expose_value=False,
)
@click.pass_obj
def show_curvpaths(
    curvctx: CurvContext,
) -> None:
    """Show the interpolatedpaths read from the path_raw.env file"""

    curv_paths = curvctx.make_paths()

    if int(curvctx.args.get("verbosity", 0)) >= 2:
        profile = curvctx.profile
        profile_name = profile.name
        board_toml = curv_paths["CURV_CONFIG_BOARD_TOML_PATH"]
        board_name = curv_paths["CURV_CONFIG_BOARD_TOML_PATH"].to_path().parent.name
        device_toml = curv_paths["CURV_CONFIG_DEVICE_TOML_PATH"]
        device_name = curv_paths["CURV_CONFIG_DEVICE_TOML_PATH"].to_path().stem
        show_args: dict[str, Any] = {
            "curv_root_dir": curvctx.curv_root_dir,
            "build_dir": curvctx.build_dir,
            "profile": profile,
            "profile_name": profile_name,
            "board_toml": board_toml,
            "board_name": board_name,
            "device_toml": device_toml,
            "device_name": device_name,
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

    if argv is None:
        argv = sys.argv[1:]

    # Short-circuit version handling so it works without CURV_ROOT_DIR/CurvPaths
    if argv and ("--version" in argv or "-V" in argv):
        try:
            curvcfg.main(args=argv, standalone_mode=True)
        except SystemExit as e:
            return int(e.code)
        return 0

    def _process_early_args(argv: Optional[list[str]] = sys.argv[1:]) -> list[EarlyArg]:
        repo_fallback_curv_root_dir = None
        build_dir_fallback = Path.cwd() / REL_BUILD_DIR_DEFAULT
        try:
            repo_fallback_curv_root_dir = str(try_get_curvrootdir_git_fallback() or "")
        except Exception:
            pass
        early_curv_root_dir = EarlyArg(
            ["--curv-root-dir"], 
            env_var_fallback="CURV_ROOT_DIR", 
            default_value_fallback=repo_fallback_curv_root_dir
        )
        early_build_dir = EarlyArg(
            ["--build-dir"],
            env_var_fallback="CURV_BUILD_DIR",
            default_value_fallback=build_dir_fallback
        )
        early_profile_name = EarlyArg(
            ["--profile"],
            env_var_fallback="CURV_PROFILE",
        )
        early_board_name = EarlyArg(
            ["--board"],
            env_var_fallback="CURV_BOARD",
        )
        early_device_name = EarlyArg(
            ["--device"],
            env_var_fallback="CURV_DEVICE",
        )
        preparse([early_curv_root_dir, early_build_dir, early_profile_name, early_board_name, early_device_name], argv=argv)
        return [early_curv_root_dir, early_build_dir, early_profile_name, early_board_name, early_device_name]

    try:
        ctx_obj_kwargs = {}
        default_map_args = DefaultMapArgs()
        default_map_args.verbosity = 0
        (
            early_curv_root_dir, 
            early_build_dir,
            early_profile_name, 
            early_board_name, 
            early_device_name, 
        ) = _process_early_args()
        if early_curv_root_dir.valid:
            update_epilog_env_vars("CURV_ROOT_DIR", early_curv_root_dir.value, early_curv_root_dir.source)
            ctx_obj_kwargs["curv_root_dir"] = early_curv_root_dir.value
            default_map_args.curv_root_dir = early_curv_root_dir.value
        if early_build_dir.valid:
            update_epilog_env_vars("CURV_BUILD_DIR", early_build_dir.value, early_build_dir.source)
            ctx_obj_kwargs["build_dir"] = early_build_dir.value
            default_map_args.build_dir = early_build_dir.value
        if early_profile_name.valid:
            update_epilog_env_vars("CURV_PROFILE", early_profile_name.value, early_profile_name.source)
            ctx_obj_kwargs["profile"] = early_profile_name.value
            # cfgvars merge --profile=...
            default_map_args.profile = early_profile_name.value
        if early_board_name.valid:
            update_epilog_env_vars("CURV_BOARD", early_board_name.value, early_board_name.source)
            ctx_obj_kwargs["board"] = early_board_name.value
            # board merge --board=... and show curvpaths --board=...
            default_map_args.board = early_board_name.value
        if early_device_name.valid:
            update_epilog_env_vars("CURV_DEVICE", early_device_name.value, early_device_name.source)
            ctx_obj_kwargs["device"] = early_device_name.value
            # board merge --device=...
            default_map_args.device = early_device_name.value
        
        ctx_obj: CurvContext = CurvContext(**ctx_obj_kwargs)

        if ctx_obj and ctx_obj.curvpaths is None:
            ctx_obj.curvpaths = get_curv_paths(ctx=None, curv_root_dir=early_curv_root_dir.value, build_dir=early_build_dir.value)

        # updates some internal vars that can be set automatically once profile, device, board, etc are resolved
        default_map_args.curvpaths = ctx_obj.curvpaths

        profile_type_obj = profile_type(early_profile_name.value) if early_profile_name.valid else None
        if profile_type_obj:
            ctx_obj.profile = profile_type_obj.resolve(ctx_obj.curvpaths)
        board_type_obj = board_type(early_board_name.value) if early_board_name.valid else None
        if board_type_obj:
            ctx_obj.board = board_type_obj.resolve(ctx_obj.curvpaths)
        device_type_obj = device_type(early_device_name.value) if early_device_name.valid else None
        if device_type_obj:
            ctx_obj.device = device_type_obj.resolve(ctx_obj.curvpaths)
        
        default_map = default_map_args.to_default_map()
        curvcfg.main(
            args=argv, 
            standalone_mode=True, 
            obj=ctx_obj,
            default_map=default_map
        )
    except SystemExit as e:
        return int(e.code)
    return 0

# never executes
if __name__ == "__main__":
    sys.exit(main())
