from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING
import os
from .replace_funcs import match_vars, replace_vars

class CurvPath():
    def __init__(self, path: str|Path, PROFILE: str = None, BOARD: str = None, DEVICE: str = None, BUILD_DIR: str = None, CURV_ROOT_DIR: str = None, uninterpolated_value_info: tuple[str, dict[str, str]] = None):
        self.path_str = str(path)
        self.profile = PROFILE
        self.board = BOARD
        self.device = DEVICE
        self.build_dir = BUILD_DIR
        self.curv_root_dir = CURV_ROOT_DIR
        self._set_uninterpolated_value(uninterpolated_value_info)
        self._run_var_replacement()

    def _set_uninterpolated_value(self, uninterpolated_value_info: tuple[str, dict[str, str]]) -> None:
        if uninterpolated_value_info is not None and isinstance(uninterpolated_value_info, tuple) and len(uninterpolated_value_info) == 2:
            self.uninterpolated_value = self._recursive_uninterpolate_value(uninterpolated_value_info[0], uninterpolated_value_info[1])
        else:
            self.uninterpolated_value = None

    def _recursive_uninterpolate_value(self, value: str, env_values_uninterpolated: dict[str, str]) -> str:
        """
        Uninterpolate a value by recursively replacing $(VAR_NAME) with its own uninterpolated ${VAR_NAME}/$(VAR_NAME)
        patterns until we can replace no more.
        """
        cnt = 0
        while True:
            cnt += 1
            assert cnt < 100, "Too many iterations in _recursive_uninterpolate_value"
            # print(f"value [{cnt}]: {value}")
            var_spans = match_vars(value)
            if len(var_spans) == 0:
                break
            pos_delta = 0
            new_value = value
            for var_name, (start, end), match in var_spans:
                if var_name in env_values_uninterpolated:
                    new_value = new_value[:start + pos_delta] + env_values_uninterpolated[var_name] + new_value[end + pos_delta:]
                    pos_delta += len(env_values_uninterpolated[var_name]) - len(match)
                else:
                    new_value = new_value[:start + pos_delta] + match + new_value[end + pos_delta:]
            if new_value == value:
                break
            value = new_value
        return value

    def is_fully_resolved(self) -> bool:
        return len(match_vars(self.path_str)) == 0

    def __str__(self):
        if not self.is_fully_resolved():
            return self.path_str
        return str(Path(self.path_str).resolve())

    @staticmethod
    def _add_trailing_slash(s: str) -> str:
        if not s.endswith(os.path.sep):
            return s + os.path.sep
        return s

    def to_str(self, add_trailing_slash: bool = False) -> str:
        s = str(self)
        return CurvPath._add_trailing_slash(s) if add_trailing_slash else s

    def to_path(self) -> Path:
        return Path(str(self))

    def __repr__(self):
        resolved_str = "[resolved]" if self.is_fully_resolved() else "[unresolved]"
        return f"CurvPath({str(self)} {resolved_str})"

    def _run_var_replacement(self) -> None:
        """
        Replace all $(VAR_NAME) and ${VAR_NAME} patterns in the given string 
        with the value of the variable from this CurvPath object.
        """
        replacement_vals = {
            'PROFILE': self.profile,
            'BOARD': self.board,
            'DEVICE': self.device,
            'BUILD_DIR': str(self.build_dir) if self.build_dir is not None else None,
            'CURV_ROOT_DIR': str(self.curv_root_dir) if self.curv_root_dir is not None else None,
        }
        self.path_str = replace_vars(self.path_str, replacement_vals)
