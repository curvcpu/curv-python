from __future__ import annotations
import click
from rich.traceback import install
from rich.console import Console
from curvpyutils.shellutils import get_console_width
from pathlib import Path
from curvtools.cli.curvcfg.cli_helpers.help_formatter import CurvcfgHelpFormatterGroup, set_epilog_fn
from curvtools.cli.curvcfg.cli_helpers.opts.curv_root_dir_opt import shell_complete_curv_root_dir
from curvtools.cli.curvcfg.cli_helpers.opts.build_dir_opts import shell_complete_build_dir
from curvtools.cli.curvcfg.cli_helpers.opts.version_opt import version_opt
from curvtools.cli.curvcfg.lib.curv_paths.curvcontext import CurvContext
from curvtools.cli.curvcfg.lib.curv_paths import try_get_curvrootdir_git_fallback
from typing import Optional
import sys

CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
}

@click.group()
@click.option(
    "--curv-root-dir",
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True, exists=True),
    required=False,
    help="CurvCPU project root directory; defaults to CURV_ROOT_DIR environment variable with fallback to current repo root if you're in a git repo.",
    envvar="CURV_ROOT_DIR",
    shell_complete=shell_complete_curv_root_dir,
)
@click.option(
    "--build-dir",
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True, exists=False),
    required=False,
    help="Build output directory",
    envvar="CURV_BUILD_DIR",
    shell_complete=shell_complete_build_dir,
)
@version_opt()
@click.pass_context
def curvcfg(ctx: click.Context, curv_root_dir: Optional[str], build_dir: Optional[str]):
    """
    CURV configuration tool.
    """
    curvctx = ctx.ensure_object(CurvContext)
    curvctx.curv_root_dir = curv_root_dir
    curvctx.build_dir = build_dir
    curvctx.ctx = ctx
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
            set_epilog_fn(curv_root_dir=curv_root_dir, curv_root_dir_source=src)

########################################################
# tb and soc groups
########################################################

@curvcfg.group()
@click.pass_obj
def tb(curv: CurvContext):
    """Testbench-related commands."""
    # nothing else; we’ll call curv.make_paths_tb() in subcommands
    pass

@curvcfg.group()
@click.option(
    "--board",
    "board_name",
    required=True,
    help="Board name or path to board directory or board TOML file",
)
@click.option(
    "--device",
    "device_name",
    required=True,
    help="Device name or path to device directory or device TOML file",
)
@click.pass_context
def soc(ctx, board_name, device_name):
    """SoC-related commands."""
    curvctx = ctx.ensure_object(CurvContext)
    curvctx.board = board_name
    curvctx.device = device_name


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
