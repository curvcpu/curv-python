#!/usr/bin/env python3

import os
import subprocess
import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.markup import escape
from curvtools import get_curvtools_version_str
from curvpyutils.file_utils.repo_utils import get_git_repo_root
from curvpyutils.system import UserConfigFile
from rich.console import Console
from rich.traceback import install, Traceback
from typing import Any, Optional
from curvtools import constants
import json
from rich.json import JSON
from pathlib import Path

install(show_locals=True, width=120, word_wrap=True)

console = Console()
err_console = Console(file=sys.stderr)

CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
}

PROGRAM_NAME = "curvtools"

def make_user_config_file() -> UserConfigFile:
    return UserConfigFile(
        app_name=constants.USER_CONFIG_FILE['APP_NAME'], 
        app_author=constants.USER_CONFIG_FILE['APP_AUTHOR'], 
        filename=constants.USER_CONFIG_FILE['FILENAME']
    )

def get_curv_python_repo_path(quiet: bool = False, cwd: str = os.getcwd()) -> Optional[str]:
    curr_dir_ok = False
    cmd = ["git", "remote", "get-url", "--all", "origin"]
    res = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd
    )
    if res.returncode != 0:
        if not quiet:
            raise ValueError("Config file can only be initially created while in the curv-python clone directory")
        else:
            return None
    for line in res.stdout.splitlines():
        if 'curvcpu/curv-python.git' in line:
            curr_dir_ok = True
            break
    if not curr_dir_ok:
        if not quiet:
            raise ValueError("Config file can only be initially created while in the curv-python clone directory")
        else:
            return None
    else:
        return get_git_repo_root(cwd=cwd)
    
def is_plausible_repo_dir(repo_dir: Optional[str], verbose: bool = False) -> bool:
    repo_dir = repo_dir or os.getcwd()
    res = get_curv_python_repo_path(quiet=not verbose, cwd=repo_dir)
    if res is None:
        if verbose:
            console.print(f"Repo directory {repo_dir} is not plausible", highlight=False, style="bold red")
        return False
    else:
        ret = Path(res).resolve() == Path(repo_dir).resolve()
        if verbose:
            console.print(f"Repo directory {repo_dir} is plausible: [bold green]{ret}[/bold green]", highlight=False, style="sky_blue3")
        return ret

def get_initial_dict(quiet: bool = False, cwd: Optional[str] = None) -> dict[str, Any]:
    cwd = cwd or os.getcwd()
    initial_dict = {
        "curvtools": {
            "CURV_PYTHON_EDITABLE_REPO_PATH": get_curv_python_repo_path(quiet=quiet, cwd=cwd)
        }
    }
    return initial_dict

################################################################################
# common options
################################################################################
def verbosity_opt():
    def set_verbosity(ctx: click.Context, _param: click.Parameter, value: int) -> int: 
        ctx.ensure_object(dict)
        if "verbosity" not in ctx.obj:
            ctx.obj["verbosity"] = 0
        ctx.obj["verbosity"] = max(ctx.obj["verbosity"], min(value, 3))
        return ctx.obj["verbosity"]

    verbosity_option = click.option(
        "--verbose", '-v', 
        "verbosity",
        count=True,
        default=0, 
        show_default=True,
        help="Print verbose output (up to 3 times)",
        callback=set_verbosity,
        type=int,
    )
    def _wrap(f):
        f = verbosity_option(f)
        return f
    return _wrap

def repo_dir_opt():
    def validate_repo_dir(ctx: click.Context, _param: click.Parameter, value: str) -> str:
        if (value is None) or (value == "") or (not is_plausible_repo_dir(value, verbose=ctx.obj["verbosity"] > 0)):
            err_console.print(f"Error: --repo-dir is required and must be a git clone of `curvcpu/curv-python`", style="bold red")
            raise SystemExit(1)
        return value
    repo_dir_option = click.option("--repo-dir", '-r', 
        default=get_curv_python_repo_path(quiet=True) or None, 
        show_default=True, 
        required=True,
        help=(
            "The directory where you cloned the `curv-python` repo, "
            "which will be used to set the default value for the "
            "`CURV_PYTHON_EDITABLE_REPO_PATH` key in the config file. "
            "Must be a git clone of `curvcpu/curv-python`."
        ),
        callback=validate_repo_dir,
    )
    def _wrap(f):
        f = repo_dir_option(f)
        return f
    return _wrap

################################################################################
# CLI
################################################################################

@click.group(
    context_settings=CONTEXT_SETTINGS,
    help=(
        "This tool helps with setup for curvtools. Run `curvtools config create` from the curv-python repo directory to create the config file, then run `curvtools instructions` for instructions on how to set up the environment variables."
    ),
    epilog=(
        f"For more information, see: `{PROGRAM_NAME} instructions`"
    ),
)
@verbosity_opt()
@click.version_option(
    get_curvtools_version_str(),
    "-V", "--version",
    message=f"{PROGRAM_NAME} v{get_curvtools_version_str()}",
    prog_name=PROGRAM_NAME,
)
@click.pass_context
def cli(
    ctx: click.Context,
    verbosity: int
) -> None:
    """curvtools command line interface"""
    ctx.ensure_object(dict)
    verbose = verbosity > 0

@cli.command()
@click.pass_context
def instructions(
    ctx: click.Context
) -> None:
    """Print the instructions for setting up the shell environment"""
    console.print("\nTo make editable install of this repo work, append this line to ~/.bashrc with the following command:\n", highlight=True, style="khaki3")
    console.print(f"echo 'eval \"$({PROGRAM_NAME} shellenv)\"' >> ~/.bashrc", highlight=False, style="bold white")
    console.print("\nThen restart your shell.", highlight=True, style="khaki3")

@cli.group(name="config")
@verbosity_opt()
@click.pass_context
def config_group(
    ctx: click.Context,
    verbosity: int
) -> None:
    """
    Manage the curvtools configuration file.
    """

@config_group.command(name="show")
@click.option("--pretty", '-p', is_flag=True, default=False, help="Pretty print the config file")
@verbosity_opt()
@click.pass_context
def show_config(
    ctx: click.Context,
    pretty: bool,
    verbosity: int
) -> None:
    """
    Show the contents of the config file.
    """
    verbose = verbosity > 0
    try:
        user_config_file = make_user_config_file()
        if not user_config_file.is_readable():
            console.print(f"Warning: config file {user_config_file.config_file_path} does not exist.", highlight=True, style="bold yellow")
            return
        else:
            if pretty:
                console.print("# " + str(user_config_file.config_file_path), highlight=False, style="sky_blue3")
                console.print(JSON(json.dumps(user_config_file.read())), highlight=True, style=None)
            else:
                p = Panel(escape(user_config_file.raw_read().strip()), title=str(user_config_file.config_file_path),border_style="sky_blue3", expand=False)
                console.print(p, highlight=False, style="bold white", end="")
            return
    except ValueError as e:
        err_console.print(str(e))
        return

@config_group.command(name="create")
@repo_dir_opt()
@click.option("--force", '-f', 
    is_flag=True, 
    default=False, 
    show_default=True,
    help="Force recreation of the config file even if it already exists (default: false)")
@verbosity_opt()
@click.pass_context
def create_config(
    ctx: click.Context,
    repo_dir: str,
    force: bool,
    verbosity: int
) -> None:
    """
    Create config file with default values
    """
    verbose = verbosity > 0
    try:
        user_config_file = make_user_config_file()
        if (not user_config_file.is_readable()) or force:
            user_config_file.delete()
            user_config_file.write(get_initial_dict(quiet=not verbose, cwd=repo_dir))
            console.print(f"Config file {user_config_file.config_file_path} created or overwritten with default values.", highlight=True, style="bold green")
        else:
            console.print(f"Config file {user_config_file.config_file_path} already exists; use `--force` to force it to be re-created with default values.", highlight=True, style="yellow")
    except Exception as e:
        if verbose:
            err_console.print_exception(show_locals=True, word_wrap=True)
        else:
            err_console.print(str(e))
        return

@config_group.command(name="delete")
@verbosity_opt()
@click.pass_context
def delete_config(
    ctx: click.Context,
    verbosity: int
) -> None:
    """
    Delete existing config file.
    """
    ctx.ensure_object(dict)
    verbose = verbosity > 0
    user_config_file = make_user_config_file()
    if not user_config_file.is_readable():
        if verbose:
            console.print(f"Warning: config file {user_config_file.config_file_path} does not exist.", highlight=True, style="bold yellow")
    else:
        user_config_file.delete()
    console.print(f"Config file {user_config_file.config_file_path} deleted.", highlight=True, style="bold green")

@cli.command()
@verbosity_opt()
@click.pass_context
def shellenv(
    ctx: click.Context,
    verbosity: int
) -> None:
    """Print the shell environment variables to set"""
    ctx.ensure_object(dict)
    verbose = verbosity > 0
    user_config_file = make_user_config_file()
    try:
        if user_config_file.is_readable():
            if verbose:
                err_console.print(f"Using config file {user_config_file.config_file_path}", highlight=False, style="sky_blue3")
        else:
            err_console.print(f"Warning: config file {user_config_file.config_file_path} does not exist.\nCreate it by running `{PROGRAM_NAME} config create` from the directory where you \ngit clone'd the `curvcpu/curv-python` repo.", highlight=True, style="bold yellow")
            return
        curv_python_repo_path = user_config_file.read_kv("curvtools.CURV_PYTHON_EDITABLE_REPO_PATH")
        if curv_python_repo_path is None:
            err_console.print(f"The config file {user_config_file.config_file_path} does not contain the `CURV_PYTHON_EDITABLE_REPO_PATH` key. Run `{PROGRAM_NAME} config create --force` from the curv-python repo directory to recreate the file, or add this key manually.", style="bold red")
            return
        console.print(f"export CURV_PYTHON_EDITABLE_REPO_PATH=\"{curv_python_repo_path}\"", highlight=False, style=None)
    except Exception as e:
        if verbose:
            err_console.print_exception(show_locals=True, word_wrap=True)
        return

@cli.command()
@verbosity_opt()
@click.pass_context
def version(
    ctx: click.Context,
    verbosity: int
) -> None:
    """Print the shell environment variables for the curvtools CLI"""
    ctx.ensure_object(dict)
    verbose = verbosity > 0
    message=f"{PROGRAM_NAME} v{get_curvtools_version_str()}"
    console.print("[bold green]" + message + "[/bold green]")

def main() -> int:
    return cli.main(args=sys.argv[1:], standalone_mode=True)

if __name__ == "__main__":
    sys.exit(main())