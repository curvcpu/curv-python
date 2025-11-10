from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import make_fs_path_param_type_class, FsPathType
import click
from curvtools.cli.curvcfg.lib.globals.constants import GET_DEFAULT_BASE_CONFIG_PATH

def must_exist_callback(ctx: click.Context, param: click.Parameter, value: FsPathType) -> FsPathType:
    if not value.exists():
        raise click.ClickException(f"Base config TOML file '{value}' does not exist")
    return value

def base_config_file_opt(required: bool = False) -> click.Option:
    type_obj = make_fs_path_param_type_class(
            must_be_dir=False, 
            must_be_file=True, 
            default_value=GET_DEFAULT_BASE_CONFIG_PATH())
    return click.option(
        "--base-config-file",
        "base_config_file",
        metavar="<base-config-file>",
        default=GET_DEFAULT_BASE_CONFIG_PATH(),
        show_default=True,
        required=required,
        help="Path to base config TOML file",
        type=type_obj,
        shell_complete=type_obj.shell_complete,
        callback=must_exist_callback,
    )
