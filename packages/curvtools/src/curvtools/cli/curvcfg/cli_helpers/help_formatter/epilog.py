from typing import Callable, Optional
from click.core import ParameterSource
from pathlib import Path

_epilog_fn: Callable[[], str] = lambda: None

def _make_epilog_fn(curv_root_dir: Optional[str|Path], curv_root_dir_source: ParameterSource) -> Callable[[], str]:
    """
    Make a function that returns the epilog string for the given curv_root_dir and curv_root_dir_source.
    """
    def _epilog_fn() -> str:
        EPILOG = """
        {curv_root_dir} {curv_root_dir_source_str}
        """
        match curv_root_dir_source:
            case ParameterSource.ENVIRONMENT:
                curv_root_dir_source_str = "(env)"
            case ParameterSource.COMMANDLINE:
                curv_root_dir_source_str = "(cli)"
            case ParameterSource.DEFAULT:
                curv_root_dir_source_str = "(repo)"
            case _:
                curv_root_dir_source_str = "(unknown)"

        if curv_root_dir is None:
            curv_root_dir_str = "not set(use --curv-root-dir to set)"
        elif not Path(curv_root_dir).absolute().resolve().is_dir():
            curv_root_dir_str = f"ERROR: not a valid directory: {curv_root_dir})"
        else:
            curv_root_dir_str = f"'{curv_root_dir}'"
        
        return EPILOG.format(
            curv_root_dir=curv_root_dir_str,
            curv_root_dir_source_str=curv_root_dir_source_str,
        )
    return _epilog_fn

def set_epilog_fn(curv_root_dir: Optional[str|Path], curv_root_dir_source: ParameterSource) -> None:
    """
    Set the epilog function.
    """
    global _epilog_fn
    _epilog_fn = _make_epilog_fn(curv_root_dir, curv_root_dir_source)

def get_epilog_fn() -> Callable[[], str]:
    """
    Get the epilog function.
    """
    return _epilog_fn
