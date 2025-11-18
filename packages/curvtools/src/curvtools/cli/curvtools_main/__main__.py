#!/usr/bin/env python3

import os
import subprocess
import sys
import click
from rich.console import Console
from curvtools import get_curvtools_version_str
from curvpyutils.file_utils.repo_utils import get_git_repo_root
from curvpyutils.system import UserConfigFile
from rich.console import Console
from rich.traceback import install, Traceback
from typing import Any
from curvtools import constants

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

def get_curv_python_repo_path() -> str:
    curr_dir_ok = False
    cmd = ["git", "remote", "get-url", "--all", "origin"]
    res = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=os.getcwd()
    )
    if res.returncode != 0:
        raise ValueError("Config file can only be initially created while in the curv-python clone directory")
    for line in res.stdout.splitlines():
        if 'curvcpu/curv-python.git' in line:
            curr_dir_ok = True
            break
    if not curr_dir_ok:
        raise ValueError("Config file can only be initially created while in the curv-python clone directory")
    else:
        return get_git_repo_root()

def get_initial_dict() -> dict[str, Any]:
    initial_dict = {
        "curvtools": {
            "CURV_PYTHON_EDITABLE_REPO_PATH": get_curv_python_repo_path()
        }
    }
    return initial_dict

@click.group(
    context_settings=CONTEXT_SETTINGS,
    help=(
        "This tool helps with setup for curvtools. Run `curvtools config create` from the curv-python repo directory to create the config file, then run `curvtools instructions` for instructions on how to set up the environment variables."
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
    """curvtools command line interface"""
    ctx.ensure_object(dict)

@cli.command()
@click.pass_context
def instructions(
    ctx: click.Context
) -> None:
    """Print the instructions for setting up the shell environment"""
    ctx.ensure_object(dict)
    console.print("\nTo make editable install of this repo work, append this line to ~/.bashrc with the following command:\n", highlight=True, style="khaki3")
    console.print(f"echo 'eval \"$({PROGRAM_NAME} shellenv)\"' >> ~/.bashrc", highlight=False, style="bold white")
    console.print("\nThen restart your shell.", highlight=True, style="khaki3")

@cli.group(name="config")
@click.pass_context
def config_group(
    ctx: click.Context
) -> None:
    """
    Manage the curvtools configuration file.
    """
    ctx.ensure_object(dict)

@config_group.command(name="create")
@click.pass_context
def create(
    ctx: click.Context
) -> None:
    """
    Create or re-create config file with default values.
    """
    ctx.ensure_object(dict)
    try:
        user_config_file = make_user_config_file()
        if not user_config_file.is_readable():
            user_config_file.delete()
            user_config_file.write(get_initial_dict())
            console.print(f"Config file {user_config_file.config_file_path} created or updated with default values.", highlight=True, style="bold green")
        else:
            console.print(f"Config file {user_config_file.config_file_path} already exists; use `{PROGRAM_NAME} config recreate` to re-create it with default values.", highlight=True, style="yellow")
    except ValueError as e:
        err_console.print(str(e))
        return

@config_group.command(name="recreate")
@click.pass_context
def recreate (
    ctx: click.Context
) -> None:
    """
    Create or re-create config file with default values.
    """
    ctx.ensure_object(dict)
    try:
        user_config_file = make_user_config_file()
        user_config_file.delete()
        user_config_file.write(get_initial_dict())
    except ValueError as e:
        err_console.print(str(e))
        return
    console.print(f"Config file {user_config_file.config_file_path} re-created with default values.", highlight=True, style="bold green")

@config_group.command(name="delete")
@click.pass_context
def delete(
    ctx: click.Context
) -> None:
    """
    Delete existing config file.
    """
    ctx.ensure_object(dict)
    user_config_file = make_user_config_file()
    user_config_file.delete()
    console.print(f"Config file {user_config_file.config_file_path} deleted.", highlight=True, style="bold green")

@cli.command()
@click.pass_context
def shellenv(
    ctx: click.Context
) -> None:
    """Print the shell environment variables to set"""
    ctx.ensure_object(dict)
    user_config_file = make_user_config_file()
    try:
        if user_config_file.is_readable():
            curv_python_repo_path = user_config_file.upsert_kv("curvtools.CURV_PYTHON_EDITABLE_REPO_PATH", get_initial_dict()["curvtools"]["CURV_PYTHON_EDITABLE_REPO_PATH"])
            console.print(f"export CURV_PYTHON_EDITABLE_REPO_PATH=\"{curv_python_repo_path}\"", highlight=False, style=None)
            return
        else:
            user_config_file.write(get_initial_dict())
            curv_python_repo_path = user_config_file.read_kv("curvtools.CURV_PYTHON_EDITABLE_REPO_PATH")
            console.print(f"export CURV_PYTHON_EDITABLE_REPO_PATH=\"{curv_python_repo_path}\"", highlight=False, style=None)
            return
    except ValueError as e:
        err_console.print(e.message)
        return
    except Exception as e:
        err_console.print_exception(show_locals=True, width=120, word_wrap=True)
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