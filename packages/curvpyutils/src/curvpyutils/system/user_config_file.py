from pathlib import Path
from platformdirs import PlatformDirs
from curvpyutils.toml_utils import read_toml_file, dump_dict_to_toml_str
from typing import Optional, Any
import os

class UserConfigFile:
    def __init__(self, app_name: str, app_author: Optional[str] = None, filename: Optional[str] = "config.toml", initial_dict: Optional[dict[str, Any]] = None):
        self.app_name = app_name      # tool name
        self.app_author = app_author  # optional; used mainly on Windows
        self.dirs = PlatformDirs(app_name, app_author)
        self.config_dir = Path(self.dirs.user_config_dir)
        os.makedirs(self.config_dir, exist_ok=True)  # platformdirs doesn't create the directory
        self.config_file = self.config_dir / filename

        # initial dict is only written if the file does not exist
        if not self.config_file.exists():
            if initial_dict is not None:
                self.config_file.write_text(dump_dict_to_toml_str(initial_dict))
            else:
                self.config_file.write_text(dump_dict_to_toml_str({}))

    def is_readable(self) -> bool:
        return os.path.isfile(self.config_file) and os.access(self.config_file, os.R_OK)
    
    def is_writeable(self) -> bool:
        return os.path.isfile(self.config_file) and os.access(self.config_file, os.W_OK)

    def read(self) -> dict[str, Any]|None:
        if not self.is_readable():
            return None
        return read_toml_file(self.config_file)


    def write(self, config: dict[str, Any]) -> None:
        if not self.is_writeable():
            return
        with open(self.config_file, "w") as f:
            f.write(dump_dict_to_toml_str(config))
    
    def clear(self) -> None:
        self.config_file.unlink(missing_ok=True)