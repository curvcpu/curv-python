import click
import os
from pathlib import Path
from curvtools.cli.curvcfg.lib.globals.constants import DEFAULT_DEP_FILE_PATH, DEFAULT_MERGED_TOML_PATH
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import make_fs_path_param_type_class, FsPathType

###############################################################################
#
# Common flags: build dir
#
###############################################################################

def build_dir_opt(must_exist: bool, help: str|None=None):
    def build_dir_callback(ctx: click.Context, _param: click.Parameter, value: FsPathType) -> FsPathType:
        ctx.obj['build_dir'] = str(Path(value).resolve()) if isinstance(value, (FsPathType, Path)) else value
        return value

    if not help:
        help = (
            "Base build directory used for both input and output."
            "By default, we look for the merged config TOML input "
            "file in <build-dir>/generated/config/merged.toml, and "
            "write generated output files under <build-dir>/generated/"
        )
    
    type_obj = make_fs_path_param_type_class(
            dir_okay=True, 
            file_okay=False, 
            must_exist=must_exist,
            default_value_if_omitted="build")
    build_dir_option = click.option(
        "--build-dir",
        "build_dir",
        metavar="<build-dir>",
        default="build",
        show_default=True,
        help=help,
        callback=build_dir_callback,
        type=type_obj,
        is_eager=True,
    )
    def _wrap(f):
        f = build_dir_option(f)
        return f
    return _wrap

