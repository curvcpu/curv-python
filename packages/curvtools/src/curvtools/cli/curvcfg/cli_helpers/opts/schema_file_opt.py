from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import make_fs_path_param_type_class, FsPathType
import click
from curvtools.cli.curvcfg.lib.globals.constants import DEFAULT_SCHEMA_TOML_PATH

def schema_file_opt(required: bool = False) -> click.Option:
    type_obj = make_fs_path_param_type_class(
            dir_okay=False, 
            file_okay=True, 
            must_exist=True,
            default_value_if_omitted=DEFAULT_SCHEMA_TOML_PATH
    )
    return click.option(
        "--schema-file",
        "schema_file_list",
        metavar="<schema-toml-file1,schema-toml-file2,...>",
        default=[DEFAULT_SCHEMA_TOML_PATH],
        show_default=True,
        required=required,
        help=(
            "Path to configuration schema TOML file. May be specified multiple times if the schema is split into multiple files.  The files will be combined, but do not override each other."
        ),
        type=type_obj,
        shell_complete=type_obj.shell_complete,
        multiple=True
    )
