import os
import shutil
import subprocess
import click
from typing import Optional, Union, Dict
import curvtools.cli.curvcfg.lib.globals.curvpaths as curvpaths
from curvtools.cli.curvcfg.lib.globals.types import CurvCliArgs

def infer_shell_from_env() -> Optional[str]:
    shell_path = os.environ.get("SHELL", "")
    if shell_path.endswith("bash"):
        return "bash"
    if shell_path.endswith("zsh"):
        return "zsh"
    if shell_path.endswith("fish"):
        return "fish"
    if os.name == "nt" and (os.environ.get("PSModulePath") or os.environ.get("ComSpec", "").endswith("powershell.exe")):
        return "powershell"
    return None


def default_install_path(shell: str, prog: str) -> str:
    if shell == "bash":
        return os.path.expanduser(f"~/.local/share/bash-completion/completions/{prog}")
    if shell == "zsh":
        path = os.environ.get("ZSH_FUNC_PATH") or os.path.expanduser("~/.zfunc")
        return os.path.join(path, f"_{prog}")
    if shell == "fish":
        return os.path.expanduser(f"~/.config/fish/completions/{prog}.fish")
    if shell == "powershell":
        return os.path.expanduser(f"~/.config/powershell/Completions/{prog}.ps1")
    raise ValueError(f"Unsupported shell: {shell}")


def _completion_env_var(prog: str) -> str:
    return f"_{prog.upper().replace('-', '_')}_COMPLETE"


def generate_completion_script(prog: str, shell: str) -> str:
    exe = shutil.which(prog) or prog
    env = os.environ.copy()
    env[_completion_env_var(prog)] = f"{shell}_source"
    res = subprocess.run([exe], env=env, check=True, capture_output=True, text=True)
    return res.stdout


def install_completion_script(script: str, target_path: str) -> None:
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w") as f:
        f.write(script)


def determine_program_name(command_path: Optional[str], info_name: Optional[str], default_prog: str) -> str:
    if command_path:
        parts = command_path.split()
        if parts:
            return parts[0]
    if info_name:
        return info_name
    return default_prog

def completions(completions_args: CurvCliArgs, prog_name: str) -> int:
    install = completions_args.get("install", False)
    install_path = completions_args.get("install_path", None)
    shell = completions_args.get("shell", None)
    
    # Determine shell and program name
    detected_shell = shell or infer_shell_from_env() or "bash"
    try:
        script = generate_completion_script(prog_name, detected_shell)
    except Exception as exc:
        raise click.ClickException(f"Failed to generate completion script via {prog_name}: {exc}")
    if not install:
        # Print to stdout so user can eval or redirect
        click.echo(script, nl=False)
        return 0

    # Install to path
    target_path = install_path or default_install_path(detected_shell, prog_name)
    try:
        install_completion_script(script, target_path)
    except PermissionError as exc:
        raise click.ClickException(f"Permission denied writing to {target_path}: {exc}")
    click.echo(f"Installed {detected_shell} completion script to {target_path}")
    return 0
