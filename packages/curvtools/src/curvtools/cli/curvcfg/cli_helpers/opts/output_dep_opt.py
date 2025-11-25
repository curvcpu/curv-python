import click
import os
from pathlib import Path
from curvtools.cli.curvcfg.lib.globals.constants import DEFAULT_DEP_FILE_PATH
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import make_fs_path_param_type_class, FsPathType

###############################################################################
#
# Common flags: output dep
#
###############################################################################

def output_dep_opt(must_exist: bool):
    # def output_dep_callback(ctx: click.Context, param: click.Parameter, value: str) -> str:
    #     if not value:
    #         value = DEFAULT_DEP_FILE_PATH
    #     from curvtools.cli.curvcfg.cli_helpers import expand_build_dir_vars
    #     value = expand_build_dir_vars(value, ctx)
    #     return os.path.abspath(value)

    type_obj = make_fs_path_param_type_class(
            dir_okay=False, 
            file_okay=True, 
            must_exist=False,
            default_value_if_omitted=DEFAULT_DEP_FILE_PATH)
    output_dep_option = click.option(
        "--dep-file",
        "dep_file",
        metavar="<dep-file-out>",
        default=DEFAULT_DEP_FILE_PATH,
        show_default=True,
        help="Makefile dependency file output path",
        # callback=output_dep_callback,
        type=type_obj,
        shell_complete=type_obj.shell_complete,
    )
    def _wrap(f):
        f = output_dep_option(f)
        return f
    return _wrap
