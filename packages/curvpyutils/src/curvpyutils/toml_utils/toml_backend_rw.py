from __future__ import annotations
from typing import Dict, Any
import curvpyutils.tomlrw

def dump_dict_to_toml_str(d: Dict[str, Any]) -> str:
    """
    Dump a dict to a TOML string using the selected backend.
    """
    return curvpyutils.tomlrw.dumps(d)


def read_toml_file(path: str) -> Dict[str, Any]:
    """
    Read and parse a TOML file into a dict.
    """
    return curvpyutils.tomlrw.loadf(path)


__all__ = [
    # Legacy/deprecated public TOML helper API
    "dump_dict_to_toml_str", 
    "read_toml_file",
]
