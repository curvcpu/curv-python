#!/usr/bin/env python3

import sys
import click
from rich.console import Console
from curvtools import get_curvtools_version_str
from curvpyutils.file_utils.repo_utils import get_git_repo_root
from curvpyutils.system import UserConfigFile
from rich.console import Console
from rich.traceback import install, Traceback

install(show_locals=True, width=120, word_wrap=True)

console = Console()
err_console = Console(file=sys.stderr)

CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
}

PROGRAM_NAME = "curvtools"

@click.group(
    # no_args_is_help=False,
    # invoke_without_command=True,
    context_settings=CONTEXT_SETTINGS,
    help=(
        "This tool helps with setup for curvtools."
    ),
    epilog=(
        f"For more information, see: `{PROGRAM_NAME} instructions`"
    ),
)
@click.version_option(
    get_curvtools_version_str(),
    "-V", "--version",
    message=f"{PROGRAM_NAME} v{get_curvtools_version_str()}",
    prog_name=PROGRAM_NAME,
)
@click.pass_context
def cli(
    ctx: click.Context,
) -> None:
    """curvtools-shellenv command line interface"""
    ctx.ensure_object(dict)
    # if ctx.invoked_subcommand is None and not ctx.resilient_parsing:
    #     ctx.invoke(instructions)

@cli.command()
@click.pass_context
def instructions(
    ctx: click.Context
) -> None:
    """Print the instructions for setting up the shell environment"""
    ctx.ensure_object(dict)
    console.print("\nTo make editable isntall of this repo work, append this line to ~/.bashrc with the following command:\n", highlight=True, style="khaki3")
    console.print(f"echo 'eval \"$({PROGRAM_NAME} shellenv)\"' >> ~/.bashrc", highlight=False, style="bold white")
    console.print("\nThen restart your shell.", highlight=True, style="khaki3")

@cli.command()
@click.pass_context
def shellenv(
    ctx: click.Context
) -> None:
    """Print the shell environment variables to set"""
    ctx.ensure_object(dict)
    user_config_file = UserConfigFile(app_name="curvtools", app_author="curv", filename="config.toml", initial_dict={
        "CURV_PYTHON_REPO_PATH": get_git_repo_root()
    })
    try:
        if user_config_file.is_readable():
            curv_python_repo_path = user_config_file.read().get("CURV_PYTHON_REPO_PATH")
            console.print(f"export CURV_PYTHON_REPO_PATH={curv_python_repo_path}", highlight=False, style=None)
            return
    except Exception as e:
        err_console.print(f"error: failed reading config file: {e}", highlight=True, style="red")
        err_console.print(Traceback.from_exception(type(e), e, e.__traceback__), highlight=False, style=None)
        raise SystemExit(1)    
    return

@cli.command()
@click.pass_context
def version(
    ctx: click.Context
) -> None:
    """Print the shell environment variables for the curvtools CLI"""
    ctx.ensure_object(dict)
    message=f"{PROGRAM_NAME} v{get_curvtools_version_str()}"
    console.print("[bold green]" + message + "[/bold green]")

def main() -> int:
    return cli.main(args=sys.argv[1:], standalone_mode=True)

if __name__ == "__main__":
    sys.exit(main())