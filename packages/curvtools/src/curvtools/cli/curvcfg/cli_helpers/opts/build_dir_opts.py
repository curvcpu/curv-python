import click
import os
from pathlib import Path
from curvtools.cli.curvcfg.lib.globals.constants import DEFAULT_DEP_FILE_PATH, DEFAULT_MERGED_TOML_PATH

###############################################################################
#
# Common flags: merged-toml-related flags
#
###############################################################################

def merged_toml_opt(name: str|None=None, outfile: bool=False):
    """
    Make a merged toml option, which can be an input file --merged-file or an output file --out-toml.
    """
    def get_merged_toml_abs_path(merged_toml_arg: str|None, ctx: click.Context) -> str:
        """
        Get the absolute path to a merged toml file.
        If the path is relative, it is resolved against the build directory.
        If the path is a bare name, it is resolved against the config directory.
        """
        from curvtools.cli.curvcfg.cli_helpers import expand_build_dir_vars
        if not merged_toml_arg:
            merged_toml_arg = DEFAULT_MERGED_TOML_PATH
        merged_toml_arg = expand_build_dir_vars(merged_toml_arg, ctx)
        merged_toml_path = Path(merged_toml_arg).absolute().resolve()
        return str(merged_toml_path)
        
    def input_merged_toml_callback(ctx: click.Context, param: click.Parameter, value: str) -> str:
        # if ctx.obj.get("verbosity") >= 3:
        #     print(f"❤️ ctx.obj: {ctx.obj}")
        if ctx.obj.get("build_dir"):
            temp_args = { "build_dir": ctx.obj.get("build_dir") }
        return get_merged_toml_abs_path(value, ctx)
    
    def output_merged_toml_callback(ctx: click.Context, param: click.Parameter, value: str) -> str:
        # if ctx.obj.get("verbosity") >= 3:
        #     print(f"❤️ ctx.obj: {ctx.obj}")
        if ctx.obj.get("build_dir"):
            temp_args = { "build_dir": ctx.obj.get("build_dir") }
        return get_merged_toml_abs_path(value, ctx)

    merged_toml_option_input_file =click.option(
        "--merged-file",
        name,
        metavar="<merged-toml-file-in>",
        default=DEFAULT_MERGED_TOML_PATH,
        show_default=True,
        help="Path to merged config TOML input file", #  Default is <build-dir>/config/merged.toml.
        callback=input_merged_toml_callback,
    )
    merged_toml_option_output_file = click.option(
        "--merged-file",
        name,
        metavar="<merged-toml-file-out>",
        default=DEFAULT_MERGED_TOML_PATH,
        show_default=True,
        help="Path to merged config TOML output file",
        callback=output_merged_toml_callback,
    )

    def _wrap(f):
        if outfile:
            f = merged_toml_option_output_file(f)
        else:
            f = merged_toml_option_input_file(f)
        return f
    return _wrap

###############################################################################
#
# Common flags: build dir
#
###############################################################################

def build_dir_opt(help: str|None=None):
    def build_dir_callback(ctx: click.Context, _param: click.Parameter, value: str) -> str:
        if not value:
            value = "build"
        abs_build_dir = os.path.abspath(value)

        if 'obj' not in ctx.obj:
            ctx.ensure_object(dict)
        ctx.obj["build_dir"] = abs_build_dir
        # if ctx.obj.get("verbosity") >= 3:
        #     print(f"💚 abs_build_dir: {abs_build_dir}")
        return abs_build_dir

    if not help:
        help = (
            "Base build directory used for both input and output."
            "By default, we look for the merged config TOML input "
            "file in <build-dir>/config/merged.toml, and write the "
            "generated output files to <build-dir>/generated."
        )
    
    build_dir_option = click.option(
        "--build-dir",
        "build_dir",
        metavar="<build-dir>",
        default="build",
        show_default=True,
        help=help,
        callback=build_dir_callback,
        is_eager=True,
    )
    def _wrap(f):
        f = build_dir_option(f)
        return f
    return _wrap

###############################################################################
#
# Common flags: output dep
#
###############################################################################

def output_dep_opt():
    def output_dep_callback(ctx: click.Context, param: click.Parameter, value: str) -> str:
        if not value:
            value = DEFAULT_DEP_FILE_PATH
        from curvtools.cli.curvcfg.cli_helpers import expand_build_dir_vars
        value = expand_build_dir_vars(value, ctx)
        return os.path.abspath(value)

    output_dep_option = click.option(
        "--dep-file",
        "dep_file",
        metavar="<dep-file-out>",
        default=DEFAULT_DEP_FILE_PATH,
        show_default=True,
        help="Makefile dependency file output path",
        callback=output_dep_callback,
    )
    def _wrap(f):
        f = output_dep_option(f)
        return f
    return _wrap