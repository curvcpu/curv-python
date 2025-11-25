from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import make_fs_path_param_type_class, FsPathType
import click
from curvtools.cli.curvcfg.lib.globals.constants import DEFAULT_PROFILE_TOML_PATH
from pathlib import Path

def profile_file_opt(required: bool = False) -> click.Option:
    type_obj = make_fs_path_param_type_class(
            dir_okay=False, 
            file_okay=True, 
            default_value_if_omitted=DEFAULT_PROFILE_TOML_PATH,
            must_exist=True)
    return click.option(
        "--profile-file",
        "profile_file",
        metavar="<profile-toml-file>",
        default=DEFAULT_PROFILE_TOML_PATH,
        show_default=True,
        required=required,
        help="Path to configuration profile TOML file",
        type=type_obj,
        shell_complete=type_obj.shell_complete,
    )
