from typing import Dict, Any, Tuple, Mapping
import sys
from . import read_toml_file, dump_dict_to_toml_str
from pathlib import Path

class CombinedTomlDict(dict[str, Any]):
    """
    Combines one or more TOML files into a single TOML dict with the option to write that dict to a new TOML file.

    The resultant dict is just the union of all the input TOML files.  There is no concept of overlaying one file on top of another.
    It is an error if two input files have the same key.
    """
    def __init__(self, toml_paths: list[str|Path]):
        super().__init__()
        toml_paths = [Path(toml).resolve() for toml in toml_paths if toml is not None]
        self.update(self._combine(toml_paths))
    
    def _combine(self, toml_paths: list[Path]) -> dict[str, Any]:
        """
        Combine the input TOML files into a single TOML dict.
        """
        result_dict = {}
        for toml_path in toml_paths:
            curr_toml_dict = read_toml_file(str(toml_path))
            for k,v in curr_toml_dict.items():
                if k in result_dict:
                    if result_dict[k] != v:
                        raise ValueError(f"duplicate key '{k}' found in input TOML file {toml_path} but with different value from p(revious file: (previous_files[k] = {result_dict[k]}) != {v} in {toml_path})")
                    else:
                        continue
            result_dict.update(curr_toml_dict)
        return result_dict