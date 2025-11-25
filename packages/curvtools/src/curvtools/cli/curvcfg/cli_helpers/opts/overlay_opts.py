import click
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import (
    make_fs_path_param_type_class,
    FsPathType,
)

###############################################################################
#
# Common flags: overlay-related flags
#
###############################################################################

def overlay_opts_for_paths_list(default: list[str]|None = None, must_exist: bool = True):
    def overlay_path_list_callback(ctx: click.Context, param: click.Parameter, value: list[FsPathType]) -> list[FsPathType]:
        assert isinstance(value, list), "value must be a list"
        assert all(isinstance(v, FsPathType) for v in value), "all values must be FsPathType"

        # if the default(s) got inserted into this list but doesn't exist, don't error out
        if default is not None:
            assert isinstance(default, list), "default must be a list"
            assert all(isinstance(d, str) for d in default), "all default values must be strings"
            for d in default:
                dp = Path(d).resolve()
                dp_exists = dp.exists()
                if dp in value and not dp_exists:
                    value.pop(value.index(dp))
        ret = [val for val in value if val is not None]
        console.print("😀😀😀 overlay_path_list_callback:\n" + f"{ret}", file=sys.stderr)
    type_obj = make_fs_path_param_type_class(
        dir_okay=False,
        file_okay=True,
        must_exist=must_exist,
        default_value_if_omitted=default)
    overlay_path_list_opt = click.option(
        "--overlay-file",
        "overlay_path_list",
        metavar="<overlay-file1,overlay-file2,...>",
        default=[default] if isinstance(default, str) else default,
        show_default=True,
        help=(
            "Path to overlay TOML files that should be applied to the profile. May be specified multiple times with, each successive file able to add to or override earlier ones."
        ),
        multiple=True,
        type=type_obj,
        shell_complete=type_obj.shell_complete,
    )
    def _wrap(f):
        f = overlay_path_list_opt(f)
        return f
    return _wrap

# def overlay_opts_for_dir_traversal():
#     type_obj = make_fs_path_param_type_class(
#         dir_okay=True, 
#         file_okay=False, 
#         must_exist=True,
#         default_value_if_omitted=".",
#     )
#     overlay_dir = click.option(
#         "--overlay-dir",
#         "overlay_dir",
#         metavar="<overlay-dir>",
#         default=".",
#         show_default=True,
#         help=(
#             "This is the lowest directory to look in for an overlay TOML file, after which we walk up the hierarchy."
#         ),
#         type=type_obj,
#         shell_complete=type_obj.shell_complete,
#     )
#     no_ascend_dir_hierarchy_opt = click.option(
#         "--ascend-dir-hierarchy/--no-ascend-dir-hierarchy",
#         "ascend_dir_hierarchy",
#         is_flag=True,
#         default=True,
#         help=(
#             "Do not ascend directories when searching for overlay toml files; "
#             "only consider the overlay directory."
#         ),
#     )

#     opts = [
#         overlay_dir, 
#         no_ascend_dir_hierarchy_opt]
    
#     # Apply in reverse so the first listed ends up nearest the function
#     def _wrap(f):
#         for opt in reversed(opts):
#             f = opt(f)
#         return f
    
#     return _wrap
