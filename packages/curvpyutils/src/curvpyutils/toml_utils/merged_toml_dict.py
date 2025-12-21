from __future__ import annotations
from typing import Dict, Any, Tuple, Mapping
import sys
from . import read_toml_file, dump_dict_to_toml_str
from pathlib import Path
from collections.abc import Mapping

################################################################################
#
# Private helper functions for the MergedTomlDict class
#
################################################################################

def _deep_merge_dicts(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively merge dictionary `overlay` into dictionary `base`.

    - If both base[key] and overlay[key] are dicts, merge them recursively.
    - Otherwise, overlay's value replaces base's value for that key.

    Returns the mutated `base` dict for convenience.
    """
    for k, v in overlay.items():
        base_v = base.get(k)
        if isinstance(base_v, dict) and isinstance(v, dict):
            _deep_merge_dicts(base_v, v)
        else:
            base[k] = v
    return base

################################################################################
#
# Public interface
#
################################################################################

class MergedTomlDict(dict[str, Any]):
    """
    Takes a base TOML file and an ordered list of overlay TOML files and merges them into a 
    single TOML dict, with option to write that dict to a new TOML file.

    The merge order is that later toml files take precedence over earlier ones.

    Paths are recommended to be absolute, but relative paths are also supported.

    The class itself is a dictionary of all values after the merge has been performed. The
    merge is deep.
    """

    # Default header comment to prepend when writing merged TOML to a file
    DEFAULT_HEADER_COMMENT: str = """
# Machine-generated file; do not edit
"""

    def __init__(self, base_toml_path: str|Path, overlay_toml_paths: list[str|Path] | None = None, header_comment: str | None = DEFAULT_HEADER_COMMENT):
        """
        Constructor.

        Args:
            base_toml_path: path to the base TOML file.
            overlay_toml_paths: list of paths to the overlay TOML files, if any; if not provided, no overlay TOML files 
                will be used and only the base TOML file will be merged into this object.
            header_comment: optional header comment to add to the top of the merged TOML file if writing to a file;
                if not provided, the default header comment will be used
        """
        # Initialize the base Dict class
        super().__init__()
        
        base_toml_path = Path(base_toml_path).resolve()
        overlay_toml_paths = [Path(toml).resolve() for toml in overlay_toml_paths or [] if toml is not None]
        self.header_comment = header_comment

        # Perform the merge and populate this dict with the merged data
        self.update(self._merge(base_toml_path, overlay_toml_paths))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], header_comment: str | None = DEFAULT_HEADER_COMMENT) -> "MergedTomlDict":
        """
        Create a MergedTomlDict from a dict[str, Any].

        Args:
            data: the dictionary to merge
            header_comment: optional header comment to add to the top of the merged TOML file if writing to a file; 
                if not provided, the default header comment will be used

        Returns:
            A MergedTomlDict object that contains the merged toml data.
        """
        from copy import deepcopy
        
        obj = cls.__new__(cls)            # bypass path-based __init__
        dict.__init__(obj)                # initialize dict base
        obj.base_toml_path = None
        obj.overlay_toml_paths = []
        obj.header_comment = header_comment
        obj.update(deepcopy(data))
        return obj

    def _merge(self, base_toml_path: Path, overlay_toml_paths: list[Path]) -> dict[str, Any]:
        """
        Merge the base and overlay TOML files into a single TOML dict which can be
        accessed using objects of this class.

        Called automatically by the constructor.
        """
        base_toml_dict = read_toml_file(str(base_toml_path))
        for overlay_toml_path in overlay_toml_paths:
            overlay_toml_dict = read_toml_file(str(overlay_toml_path))
            _deep_merge_dicts(base_toml_dict, overlay_toml_dict)
        return base_toml_dict
    
    def prepend_section(self, section_name: str, section_dict: dict[str, Any]) -> None:
        """
        In-place prepend of a new section to the merged TOML dict.
        """
        items = list(self.items())   # snapshot current order
        self.clear()
        self[section_name] = section_dict
        self.update(items)           # append the old items
    
    def append_dict(self, new_dict: Mapping[str, Any]) -> "MergedTomlDict":
        """
        In-place append of a dictionary to the merged TOML dict.

        The dictionary must not have any keys that are already in this dict.
        """
        existing = self.keys() & new_dict.keys()
        if existing:
            keys_str = ", ".join(sorted(existing))
            raise ValueError(f"keys already exist in merged TOML dict: {keys_str}")
        self.update(new_dict)
        return self
        
    def write_to_file(self, path: str|Path, write_only_if_changed: bool = True) -> bool:
        """
        Write the merged TOML dict to a file, with optional header comment.

        Args:
            path: the path to the TOML file
            write_only_if_changed: whether to write only if the file has changed

        Returns:
            True if the file was overwritten, False if it was not.
        """
        import tempfile
        import os
        import filecmp

        use_temp_file = write_only_if_changed and os.path.exists(path)
        
        # Create a temporary file for comparison if write_only_if_changed is True
        if use_temp_file:
            temp_fd, path_to_write = tempfile.mkstemp(suffix='.toml', prefix='curvcfg_')
            os.close(temp_fd)  # Close the file descriptor, we'll use the path
        else:
            path_to_write = str(path)
        
        # Write the merged TOML dict to the temporary file
        with open(path_to_write, "w") as f:
            if self.header_comment and self.header_comment.strip() != "":
                f.write(self.header_comment.strip("\n") + "\n\n")
            f.write(dump_dict_to_toml_str(self))
        
        # Compare the temporary file to the original file
        if use_temp_file:
            if filecmp.cmp(path_to_write, path, shallow=False):
                # delete the temp file if it is the same as the original
                os.remove(path_to_write)
                # return False since the original was not touched
                return False
            else:
                # the file was changed, so we need to overwrite the original file and return True
                os.rename(path_to_write, path)
                return True
        else:
            # no temp file used, so we've already overwritten the original file
            return True
        
    def split_on_top_level_key(self, key: str) -> Tuple[dict[str, Any], dict[str, Any]]:
        """
        Split the merged TOML dict into two dicts based on the top-level key.
        The first dict contains all values that start with the key; the second dict contains all values that do not.
        """
        if key not in self:
            raise KeyError(f"Key '{key}' not found in merged TOML dict")
        prefix = f"{key}."
        start_with_key_dict = {k: v for k, v in self.items() if k == key or k.startswith(prefix)}
        rest_dict = {k: v for k, v in self.items() if not (k == key or k.startswith(prefix))}
        return start_with_key_dict, rest_dict

    def get_top_level_keys(self) -> list[str]:
        """
        Get the list of top-level keys in the merged TOML dict.

        We treat only dictionary-valued entries as "top-level keys" and intentionally
        skip scalar values such as the free-form ``description`` field that may
        appear at the top of a TOML file.
        """
        return [k for k, v in self.items() if isinstance(v, dict)]
    
    def group_by_top_level_keys(self, keys: list[str] | None = None) -> dict[str, dict[str, Any]]:
        """
        Split up the merged TOML dict by top-level key.  That is, each key in ``keys``
        will become a key in the returned dictionary, with its value being a dictionary
        containing the subset of all k-v pairs in the merged TOML dict whose keys start
        with that top-level key.
        
        The merged TOML dict is not modified.
        
        Args:
            keys: the list of top-level keys to split the merged TOML dict by. 
             - If ``keys`` is None or empty, then the split will be across all
               top-level keys (as returned by ``get_top_level_keys()``).
             - If ``keys`` is a list of one or more keys, then only those keys
               will be split out.
             - If ``keys`` contains a key that is not a top-level key, then the
               returned dictionary will contain that key mapped onto an empty
               dictionary.
        
        Returns:
            A dictionary with its keys being those in the ``keys`` argument (or
            all top-level keys if ``keys`` was None or empty), mapping onto all
            the corresponding sub-dictionaries as values.
        
        Note: the inner values dictionary in the returned value uses as its
        string keys the full keys of the merged TOML dict; top-level keys are
        not stripped.
        """
        # Decide which top-level keys we are grouping by.
        if not keys:
            group_keys = self.get_top_level_keys()
        else:
            group_keys = list(keys)

        grouped: dict[str, dict[str, Any]] = {}

        # For each requested group key, collect all entries in this dict whose
        # keys either exactly match the group key or begin with "<group_key>.".
        # The latter form is useful if the MergedTomlDict is ever used in a
        # flattened, dot-separated representation.
        for gkey in group_keys:
            prefix = f"{gkey}."
            grouped[gkey] = {
                k: v
                for k, v in self.items()
                if k == gkey or k.startswith(prefix)
            }

        return grouped

__all__ = ["MergedTomlDict"]