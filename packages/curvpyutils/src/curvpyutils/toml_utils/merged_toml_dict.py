from typing import Dict, Any, Tuple, Mapping
import sys
from . import read_toml_file, dump_dict_to_toml_str
from pathlib import Path

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

class MergedTomlDict(Dict[str, Any]):
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

    def __init__(self, base_toml_path: str, overlay_toml_paths: list[str] | None = None, header_comment: str | None = DEFAULT_HEADER_COMMENT):
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
        
        self.base_toml_path = base_toml_path
        self.overlay_toml_paths = overlay_toml_paths or []
        self.header_comment = header_comment

        # Perform the merge and populate this dict with the merged data
        self.update(self._merge())

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

    @classmethod
    def from_toml_files(cls, base_toml_path: str, overlay_toml_paths: list[str] | None = None, header_comment: str | None = DEFAULT_HEADER_COMMENT) -> "MergedTomlDict":
        """
        Create a MergedTomlDict from a base TOML file and zero or more overlay TOML files.

        Args:
            base_toml_path: the path to the base TOML file
            overlay_toml_paths: a list of paths to the overlay TOML files
            header_comment: optional header comment to add to the top of the merged TOML file for when later 
                writing to a file; if not provided, the default header comment will be used

        Returns:
            A MergedTomlDict object that contains the merged TOML data.
        """
        return cls(base_toml_path, overlay_toml_paths or [], header_comment)

    def _merge(self) -> Dict[str, Any]:
        """
        Merge the base and overlay TOML files into a single TOML dict which can be
        accessed using objects of this class.

        Called automatically by the constructor.
        """
        base_toml_dict = read_toml_file(self.base_toml_path)
        for overlay_toml_path in self.overlay_toml_paths:
            overlay_toml_dict = read_toml_file(overlay_toml_path)
            _deep_merge_dicts(base_toml_dict, overlay_toml_dict)
        return base_toml_dict
    
    def prepend_section(self, section_name: str, section_dict: Dict[str, Any]) -> None:
        """
        In-place prepend of a new section to the merged TOML dict.
        """
        items = list(self.items())   # snapshot current order
        self.clear()
        self[section_name] = section_dict
        self.update(items)           # append the old items
    
    def write_to_file(self, path: str, write_only_if_changed: bool = True, append_contents_of_file: str | Path = None) -> bool:
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
            path_to_write = path
        
        # Write the merged TOML dict to the temporary file
        with open(path_to_write, "w") as f:
            if self.header_comment and self.header_comment.strip() != "":
                f.write(self.header_comment.strip("\n") + "\n\n")
            f.write(dump_dict_to_toml_str(self))

        # If we were asked to append the contents of a file, then add it now.
        if append_contents_of_file:
            with open(path_to_write, "a") as f_out:
                f_out.write("\n\n")
                with open(append_contents_of_file, "r") as f_in:
                    f_out.write(f_in.read())
        
        # Compare the temporary file to the original file
        if use_temp_file:
            if filecmp.cmp(path_to_write, path):
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
        
    def split_on_top_level_key(self, key: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Split the merged TOML dict into two dicts based on the top-level key.
        The first dict contains all values that start with the key; the second dict contains all values that do not.
        """
        if key not in self:
            raise KeyError(f"Key '{key}' not found in merged TOML dict")
        start_with_key_dict = {k: v for k, v in self.items() if k.startswith(key)}
        rest_dict = {k: v for k, v in self.items() if not k.startswith(key)}
        return start_with_key_dict, rest_dict


__all__ = ["MergedTomlDict"]