from typing import Callable, Optional
from click.core import ParameterSource
from pathlib import Path

class EpilogEnvVarValue:
    env_var_value: Optional[str]
    env_var_source: ParameterSource
    def __init__(self, env_var_value: Optional[str|Path], env_var_source: ParameterSource):
        self.env_var_value = str(env_var_value) if env_var_value is not None else ""
        self.env_var_source = env_var_source
    def __str__(self):
        return f"{self.env_var_value} {_get_source_str(self.env_var_source)}"
    def __repr__(self):
        return self.__str__()

_epilog_fn: Callable[[], str] = lambda: None
epilog_env_vars: dict[str, EpilogEnvVarValue] = {}

def _get_source_str(source: ParameterSource) -> str:
    match source:
        case ParameterSource.ENVIRONMENT:
            return "(env)"
        case ParameterSource.COMMANDLINE:
            return "(cli)"
        case ParameterSource.DEFAULT_MAP:
            return "(repo or default)"
        case ParameterSource.DEFAULT:
            return "(repo or default)"
        case _:
            return "(not set)"

def _make_epilog_fn(set_epilog_fn_arg_list: list[tuple[str, Optional[str|Path], ParameterSource]]) -> Callable[[], str]:
    """
    Make a function that returns the epilog string for the given curv_root_dir and curv_root_dir_source.
    """
    global epilog_env_vars
    for key, value, source in set_epilog_fn_arg_list:
        if value is not None and key not in epilog_env_vars.keys():
            epilog_env_vars[key] = EpilogEnvVarValue(value, source)
    def _epilog_fn() -> str:
        max_key_len = max(len(k) for k in epilog_env_vars.keys())
        EPILOG = ""
        for k, env_var_value in epilog_env_vars.items():
            if not env_var_value:
                continue
            value_str = f"{Path(env_var_value.env_var_value).resolve().as_posix()}"
            src_str = _get_source_str(env_var_value.env_var_source)
            EPILOG += f"• {k:<{max_key_len}} = {value_str} {src_str}\n\n"
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
