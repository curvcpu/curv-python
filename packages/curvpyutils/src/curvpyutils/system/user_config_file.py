from pathlib import Path
from platformdirs import PlatformDirs
from curvpyutils.toml_utils import read_toml_file, dump_dict_to_toml_str
from typing import Optional, Any
import os
import shutil
import copy

class UserConfigFile:
    def __init__(self, 
        app_name: str, 
        app_author: Optional[str] = None, 
        filename: Optional[str] = "config.toml"
    ):
        self.app_name = app_name      # tool name
        self.app_author = app_author  # optional; used mainly on Windows
        self.config_file_path = self.get_config_dirpath() / filename

        # # initial dict is only written if the file does not exist
        # if not self.config_file_path.exists():
        #     if initial_dict is not None:
        #         self.write(initial_dict)
        #     else:
        #         self.write({})

    def get_config_dirpath(self) -> Path:
        """
        Return the path to the entire config directory.
        """
        self.dirs = PlatformDirs(self.app_name, self.app_author)
        return Path(self.dirs.user_config_dir)

    def get_config_filepath(self) -> Path:
        """
        Return the path to the config directory and the config file.
        """
        return self.config_file_path

    def is_readable(self) -> bool:
        """
        Return True if the config file both exists and is
        readable.
        """
        # print(f"exists: {os.path.exists(self.config_file_path)}")
        # print(f"isfile: {os.path.isfile(self.config_file_path)}")
        # print(f"readable: {os.access(self.config_file_path, os.R_OK)}")
        return (
            os.path.exists(self.config_file_path) and
            os.path.isfile(self.config_file_path) and 
            os.access(self.config_file_path, os.R_OK)
        )
    
    def read(self) -> dict[str, Any]:
        toml_dict = read_toml_file(self.config_file_path)
        return toml_dict

    def raw_read(self) -> str:
        """
        Read the config file as a raw string.
        """
        return self.config_file_path.read_text(encoding="utf-8")

    def _dotted_path_to_list(self, path: str) -> list[str]:
        return path.split(".")

    _MISSING = object()
    def read_kv(self, path: str, default: Any = _MISSING) -> Any:
        """
        Read a key-value pair from the config file. If the key
        does not exist, return the default value.

        Args:
            path: dotted path to the key-value pair to read
            default: default value to return if the key does not exist

        Returns:
            the value of the key-value pair, or the default value 
            if the key does not exist.
        """
        d = self.read()
        for p in self._dotted_path_to_list(path):
            if not isinstance(d, dict) or p not in d:
                if default is self._MISSING:
                    raise KeyError(path)
                return default
            d = d[p]
        return d
    
    def upsert_kv(self, path: str, value: Any) -> Any:
        """
        Upsert a key-value pair into the config file. If the key
        does not exist, create it. If the key exists and is not a
        dict, overwrite it with a new dict.

        Args:
            path: dotted path to the key-value pair to upsert
            value: value to upsert

        Returns:
            the value that was upserted. If the key did not exist,
            return the default value.
        """
        parts = self._dotted_path_to_list(path)
        if not parts:
            raise ValueError("path must be a non-empty dotted string")

        cfg = self.read()
        d: dict[str, Any] = cfg

        for key in parts[:-1]:
            # If the key doesn't exist or isn't a dict, overwrite with a new dict.
            if key not in d or not isinstance(d[key], dict):
                d[key] = {}
            d = d[key]  # now guaranteed to be a dict
        last_key = parts[-1]
        d[last_key] = value
        self.write(cfg)
        return d[last_key]

    def write(self, config: dict[str, Any]) -> None:
        os.makedirs(self.get_config_dirpath(), exist_ok=True)
        self.config_file_path.write_text(
            data=(
                f"# {self.app_name} config file\n\n" +
                dump_dict_to_toml_str(config)
            ),
            encoding="utf-8"
        )
    
    def delete(self) -> None:
        """
        Delete the config file. If there is nothing left in the
        config dir, remove the entire config dir as well.
        """
        if os.path.exists(self.config_file_path):
            self.config_file_path.unlink()
        assert not os.path.exists(self.config_file_path), f"Config file still exists: {self.config_file_path}"
        
        config_dir_path = self.get_config_dirpath()
        if os.path.exists(config_dir_path):
            if len(os.listdir(config_dir_path)) == 0:
                shutil.rmtree(config_dir_path)
                assert not os.path.exists(config_dir_path), f"Config dir still exists: {config_dir_path}"