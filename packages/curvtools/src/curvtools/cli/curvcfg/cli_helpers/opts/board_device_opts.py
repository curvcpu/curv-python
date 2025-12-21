import click
from typing import Callable, Any
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import make_fs_path_param_type_class, FsPathType
from ...lib.curv_paths import get_curv_paths
from enum import Enum
from pathlib import Path
import os
import sys

###############################################################################
#
# Common flags: boardand device
#
###############################################################################

class Kind(Enum):
    TB = "tb"
    SOC = "soc"

def kind_opts(default_kind: Kind = Kind.SOC) -> Callable[[Callable[[click.Context], Any]], Callable[[click.Context], Any]]:
    def kind_callback(ctx: click.Context, _param: click.Parameter, value: FsPathType) -> FsPathType:
        ctx.obj['kind'] = value
        return value

    tb_option = click.option(
        "--tb",
        "kind",                     # same destination name
        flag_value=Kind.TB,         # value to assign if this flag is used
        default=True if default_kind == Kind.TB else False,
        help="Use testbench build mode",
    )
    soc_option = click.option(
        "--soc",
        "kind",                      # same destination name
        flag_value=Kind.SOC,         # value to assign if this flag is used
        default=True if default_kind == Kind.SOC else False,
        help="Use SoC build mode",
    )
    opts = [
        tb_option,
        soc_option,
    ]
    def _wrap(f):
        for opt in reversed(opts):
            if opt is not None:
                f = opt(f)
        return f
    return _wrap

def board_device_opts(default_board_name: str|None = None, default_device_name: str|None = None) -> Callable[[Callable[[click.Context], Any]], Callable[[click.Context], Any]]:
    def board_callback(ctx: click.Context, _param: click.Parameter, value: FsPathType) -> FsPathType:
        ctx.obj['board'] = str(value.resolve()) if isinstance(value, (FsPathType, Path)) else value
        return ctx.obj['board']
    def device_callback(ctx: click.Context, _param: click.Parameter, value: FsPathType) -> FsPathType:
        ctx.obj['device'] = str(value.resolve()) if isinstance(value, (FsPathType, Path)) else value
        return ctx.obj['device']

    try:
        curvpaths = get_curv_paths()
    except Exception as e:
        curvpaths = None

    board_prefix = ""
    device_prefix = ""
    if curvpaths is not None:
        try:
            board_prefix = str(curvpaths['CURV_BOARDS_DIR']) + os.path.sep
        except KeyError:
            pass
        try:
            device_prefix = str(curvpaths['CURV_CONFIG_DEVICES_DIR']) + os.path.sep
        except KeyError:
            pass
    
    board_type_obj = make_fs_path_param_type_class(
            dir_okay=True, 
            file_okay=False, 
            must_exist=False,
            default_value_if_omitted=default_board_name,
            raw_string_handling={
                "prefix": board_prefix, 
                "suffix": ""}
    )
    board_option = click.option(
        "--board-dir", "--board",
        "board_dir",
        metavar="<board>",
        default=default_board_name,
        show_default=True,
        help="Name of board to use or path to board TOML file (ignored in testbench builds)",
        callback=board_callback,
        type=board_type_obj,
    )
    device_type_obj = make_fs_path_param_type_class(
            dir_okay=False, 
            file_okay=True, 
            must_exist=False,
            default_value_if_omitted=default_device_name,
            raw_string_handling={
                "prefix": device_prefix, 
                "suffix": ".toml"}
    )
    device_option = click.option(
        "--device-toml", "--device",
        "device_toml",
        metavar="<device>",
        default=default_device_name,
        show_default=True,
        help="Name of device to use or path to device TOML file (ignored in testbench builds)",
        callback=device_callback,
        type=device_type_obj,
    )

    opts = [
        board_option,
        device_option,
    ]
    def _wrap(f):
        for opt in reversed(opts):
            if opt is not None:
                f = opt(f)
        return f
    return _wrap
