from typing import Callable, Optional
from click.core import ParameterSource
from pathlib import Path

_epilog_fn: Callable[[], str] = lambda: None

def _get_source_str(source: ParameterSource) -> str:
    match source:
        case ParameterSource.ENVIRONMENT:
            return "(env)"
        case ParameterSource.COMMANDLINE:
            return "(cli)"
        case ParameterSource.DEFAULT_MAP:
            return "(repo)"
        case ParameterSource.DEFAULT:
            return "(repo)"
        case _:
            return "(not set)"

def _make_epilog_fn(set_epilog_fn_arg_list: list[tuple[str, Optional[str|Path], ParameterSource]]) -> Callable[[], str]:
    """
    Make a function that returns the epilog string for the given curv_root_dir and curv_root_dir_source.
    """
    def _epilog_fn() -> str:
        max_key_len = max(len(key) for key, _, _ in set_epilog_fn_arg_list)
        EPILOG = ""
        for key, value, source in set_epilog_fn_arg_list:
            if value is None:
                dir_str = "not set (use cli arguments or env var {key}=<path> to set)"
            else:
                dir_str = f"{Path(value).resolve().as_posix()}"
            EPILOG += f"{key:<{max_key_len}} = {dir_str} {_get_source_str(source)}\n"
        return EPILOG
    return _epilog_fn

def set_epilog_fn(set_epilog_fn_arg_list: list[tuple[str, Optional[str|Path], ParameterSource]]) -> None:
    """
    Set the epilog function.
    """
    global _epilog_fn
    _epilog_fn = _make_epilog_fn(set_epilog_fn_arg_list)

def get_epilog_fn() -> Callable[[], str]:
    """
    Get the epilog function.
    """
    return _epilog_fn
