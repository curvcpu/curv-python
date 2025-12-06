from __future__ import annotations
import os
import subprocess
from curvpyutils.shellutils import Which
from pathlib import Path
import tempfile
import shutil
from subprocess import CalledProcessError
from curvpyutils.toml_utils import dump_dict_to_toml_str, read_toml_file    
from typing import Optional
from collections import OrderedDict

class TomlCanonicalizer:
    @staticmethod
    def _is_readable(path: Path) -> bool:
        """Check if the file at path is readable."""
        return os.access(path, os.R_OK)

    @staticmethod
    def _is_writable(path: Path) -> bool:
        """Check if the file at path is writable."""
        return os.access(path, os.W_OK)

    def __init__(self, input_file: Path, silent: bool = False) -> None:
        assert Path(input_file).is_absolute(), "input_file must be an absolute path"
        assert Path(input_file).exists() and Path(input_file).is_file() and self._is_readable(Path(input_file)), "input_file must be a file that exists and is readable"
        self.silent = silent
        self.input_file = input_file
        self.temp_file = self._copy_input_file_to_temp_file()
        self.taplo_cmd = self._get_taplo_cmd()
        if self.taplo_cmd is not None:
            self._taplo_in_place_rewrite()
        else:
            self._canonicalize_with_python_toml()

    def overwrite_input_file(self) -> bool:
        """
        Overwrite the input file with the canonicalized version.
        """
        assert self.temp_file.exists() and self.temp_file.is_file() and self._is_readable(self.temp_file), "temp_file must be a file that exists and is readable"
        assert Path(self.input_file).exists() and Path(self.input_file).is_file() and self._is_writable(Path(self.input_file)), "input_file must be a file that exists and is writable"
        try:
            os.rename(self.temp_file, self.input_file)
        except Exception as e:
            raise Exception(f"failed to overwrite input file: {e}")
        return True

    def _get_taplo_cmd(self) -> Optional[Path]:
        try:
            return Which('taplo', on_missing_action=Which.OnMissingAction.RAISE)()
        except FileNotFoundError:
            return None

    def _copy_input_file_to_temp_file(self) -> Path:
        """
        Copy the input TOML file to a temporary file.
        """
        temp_file = Path(tempfile.mkstemp(suffix='.toml', prefix='taplo_toml_temp_')[1])
        shutil.copy(self.input_file, temp_file)
        return temp_file

    def _taplo_in_place_rewrite(self) -> None:
        """
        Run taplo to canonicalize a single TOML file.
        """
        # IMPORTANT:  taplo can go berserk and reformat everything recursively under 
        # the current working directory, so it's essential to make sure you pass it
        # only the path to a single, extant file!
        if not self.temp_file.exists() or not self.temp_file.is_file():
            raise ValueError(f"TOML file is not a file: {self.temp_file}")

        try:
            result = subprocess.run(
                [   self.taplo_cmd, 
                    'fmt', 
                    '-o', 'align_entries=true', 
                    '-o', 'array_trailing_comma=true', 
                    '-o', 'reorder_keys=true', 
                    '-o', 'array_auto_expand=true', 
                    '-o', 'array_auto_collapse=false', 
                    '-o', 'compact_arrays=false', 
                    self.temp_file ], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                check=True
            )
        except CalledProcessError as e:
            raise CalledProcessError(f"taplo returned non-zero (exit code {e.returncode}): {e.stderr}")
        if not self.silent:
            print(f"taplo output: {result.stdout}")
            print(f"taplo stderr: {result.stderr}")
            print(f"taplo return code: {result.returncode}")
            print(f"taplo temp file: {self.temp_file}")
            print(f"taplo input file: {self.input_file}")

    def _canonicalize_with_python_toml(self) -> None:
        """
        Canonicalize a TOML file with python-toml.
        """
        # Sort the dictionary keys alphabetically
        def sort_obj(x):
            if isinstance(x, dict):
                # sort keys alphabetically
                return OrderedDict((k, sort_obj(x[k])) for k in sorted(x))
            elif isinstance(x, list):
                # if you want to keep array order, just recurse:
                return [sort_obj(v) for v in x]
                # or, for certain keys you know are sets, sort them explicitly
            else:
                return x
        
        if not self.silent:
            print(f"canonicalizing with python-toml: {self.temp_file}")
        d = read_toml_file(str(self.temp_file))
        data = sort_obj(d)
        s = dump_dict_to_toml_str(data)
        with open(self.temp_file, 'w') as f:
            f.write(s)