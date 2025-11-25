import click
import os
from pathlib import Path
from curvtools.cli.curvcfg.lib.globals.constants import DEFAULT_MERGED_TOML_PATH
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import make_fs_path_param_type_class, FsPathType

###############################################################################
#
# Common flags: merged-toml-related flags
#
###############################################################################

def merged_toml_input_opt(name: str|None=None):
    """
    Make a merged toml option, which must be an input file.
    """
    # def get_merged_toml_abs_path(merged_toml_arg: str|None, ctx: click.Context) -> str:
    #     """
    #     Get the absolute path to a merged toml file.
    #     If the path is relative, it is resolved against the build directory.
    #     If the path is a bare name, it is resolved against the config directory.
    #     """
    #     from curvtools.cli.curvcfg.cli_helpers import expand_build_dir_vars
    #     if not merged_toml_arg:
    #         merged_toml_arg = DEFAULT_MERGED_TOML_PATH
    #     merged_toml_arg = expand_build_dir_vars(merged_toml_arg, ctx)
    #     merged_toml_path = Path(merged_toml_arg).absolute().resolve()
    #     return str(merged_toml_path)
        
    # def input_merged_toml_callback(ctx: click.Context, param: click.Parameter, value: str) -> str:
    #     # if ctx.obj.get("verbosity") >= 3:
    #     #     print(f"❤️ ctx.obj: {ctx.obj}")
    #     # if ctx.obj.get("build_dir"):
    #     #     temp_args = { "build_dir": ctx.obj.get("build_dir") }
    #     return get_merged_toml_abs_path(value, ctx)
    
    type_obj = make_fs_path_param_type_class(
            dir_okay=False, 
            file_okay=True, 
            default_value_if_omitted=DEFAULT_MERGED_TOML_PATH,
            must_exist=True)
    merged_toml_option_input_file =click.option(
        "--merged-file",
        name,
        metavar="<merged-toml-file-in>",
        default=DEFAULT_MERGED_TOML_PATH,
        show_default=True,
        help="Path to merged config TOML input file", #  Default is <build-dir>/config/merged.toml.
        type=type_obj,
        shell_complete=type_obj.shell_complete,
        # callback=input_merged_toml_callback,
    )

    def _wrap(f):
        f = merged_toml_option_input_file(f)
        return f
    return _wrap


def merged_toml_output_opt(name: str|None=None):
    """
    Make a merged toml option, which must be an output file.
    """
    # def get_merged_toml_abs_path(merged_toml_arg: str|None, ctx: click.Context) -> str:
    #     """
    #     Get the absolute path to a merged toml file.
    #     If the path is relative, it is resolved against the build directory.
    #     If the path is a bare name, it is resolved against the config directory.
    #     """
    #     from curvtools.cli.curvcfg.cli_helpers import expand_build_dir_vars
    #     if not merged_toml_arg:
    #         merged_toml_arg = DEFAULT_MERGED_TOML_PATH
    #     merged_toml_arg = expand_build_dir_vars(merged_toml_arg, ctx)
    #     merged_toml_path = Path(merged_toml_arg).absolute().resolve()
    #     return str(merged_toml_path)
            
    # def output_merged_toml_callback(ctx: click.Context, param: click.Parameter, value: str) -> str:
    #     # if ctx.obj.get("verbosity") >= 3:
    #     #     print(f"❤️ ctx.obj: {ctx.obj}")
    #     # if ctx.obj.get("build_dir"):
    #     #     temp_args = { "build_dir": ctx.obj.get("build_dir") }
    #     return get_merged_toml_abs_path(value, ctx)

    type_obj = make_fs_path_param_type_class(
            dir_okay=False, 
            file_okay=True, 
            default_value_if_omitted=DEFAULT_MERGED_TOML_PATH,
            must_exist=False)
    merged_toml_option_output_file = click.option(
        "--merged-file",
        name,
        metavar="<merged-toml-file-out>",
        default=DEFAULT_MERGED_TOML_PATH,
        show_default=True,
        help="Path to merged config TOML output file",
        type=type_obj,
        shell_complete=type_obj.shell_complete,
        # callback=output_merged_toml_callback,
    )

    def _wrap(f):
        f = merged_toml_option_output_file(f)
        return f
    return _wrap
