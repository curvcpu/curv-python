import os
from pathlib import Path
from typing import Dict, Union, Optional
from rich import get_console
from curvpyutils.file_utils.repo_utils import get_git_repo_root
from curvtools.cli.curvcfg.lib.globals.curvpaths_temporary import get_curv_root_dir_from_repo_root
from dotenv import dotenv_values
from curvtools.cli.curvcfg.lib.globals.types import CurvCliArgs
from click import Context
from click.core import ParameterSource

curvpaths: Optional[Dict[str, Path]] = None
_curvroot_dir_source: Optional[ParameterSource] = None

class CurvPaths(dict[str, Path]):
    def __init__(self, curv_root_dir: str):
        super().__init__()
        self._set_paths(curv_root_dir)
        
    def _set_paths(self, curv_root_dir: str):
        env_path = os.path.join(curv_root_dir, "scripts", "make", "paths_raw.env")
        if not os.path.isfile(env_path):
            get_console().print(f"[red]error:[/red] paths environment file not found: {env_path}")
            raise SystemExit(1)
        if "CURV_ROOT_DIR" not in os.environ:
            os.environ["CURV_ROOT_DIR"] = curv_root_dir
        env_dict = dotenv_values(dotenv_path=env_path, interpolate=True, encoding="utf-8", verbose=True)
        self["CURV_ROOT_DIR"] = Path(curv_root_dir)
        self["CURV_REPO_DIR"] = Path(env_dict.get("CURV_REPO_DIR", f"{curv_root_dir}/../..")).resolve()
        self["CURV_CONFIG_DIR"] = Path(env_dict.get("CURV_CONFIG_DIR", f"{curv_root_dir}/config")).resolve()
        self["CURV_RISCV_DIR"] = Path(env_dict.get("CURV_RISCV_DIR", f"{curv_root_dir}/riscv")).resolve()
        self["CURV_COMMON_DIR"] = Path(env_dict.get("CURV_COMMON_DIR", f"{curv_root_dir}/../common")).resolve()
        self["CURV_FIRMWARE_DIR"] = Path(env_dict.get("CURV_FIRMWARE_DIR", f"{curv_root_dir}/riscv/firmware")).resolve()

    def __str__(self):
        s = ""
        for k,v in self.items():
            s += f"{k}: {v}\n"
        s = s[:-1]
        return s

    def get_config_dir(self, add_trailing_slash: bool = False) -> str:
        s = str(self["CURV_CONFIG_DIR"])
        if add_trailing_slash and not s.endswith(os.path.sep):
            s += os.path.sep
        return s

    def get_curv_root_dir(self, add_trailing_slash: bool = False) -> str:
        s = str(self["CURV_ROOT_DIR"])
        if add_trailing_slash and not s.endswith(os.path.sep):
            s += os.path.sep
        return s

    def get_repo_dir(self, add_trailing_slash: bool = False) -> str:
        s = str(self["CURV_REPO_DIR"])
        if add_trailing_slash and not s.endswith(os.path.sep):
            s += os.path.sep
        return s

    # def get_schema_toml_path(self) -> str:
    #     return str(Path(self["CURV_CONFIG_DIR"]) / "schema" / "schema.toml")

    def _try_make_relative_to_dir(self,path: str, dir: str) -> str:
        """
        Try to make an absolute path into a path relative to a directory.
        If the path is not relative to the directory, return the absolute path.
        """
        # Convert both paths to absolute paths
        abs_path = Path(path).absolute()
        abs_dir = Path(dir).absolute()
        if not abs_path.is_relative_to(abs_dir):
            return str(abs_path)
        else:
            return str(abs_path.relative_to(abs_dir))

    def mk_rel_to_curv_root(self, abs_path: str) -> str:
        """
        Try to make an absolute path into a path relative to the curv root directory.
        If the path is not relative to the curv root directory, return the absolute path.
        """
        return self._try_make_relative_to_dir(abs_path, self.get_curv_root_dir())

    def mk_rel_to_cwd(self, abs_path: str) -> str:
        """
        Try to make an absolute path into a path relative to a directory.
        If the path is not relative to the directory, return the absolute path.
        """
        return self._try_make_relative_to_dir(abs_path, os.getcwd())

    def mk_rel_to_curv_config_dir(self, abs_path: str) -> str:
        """
        Try to make an absolute path into a path relative to the curv config directory.
        If the path is not relative to the curv config directory, return the absolute path.
        """
        return self._try_make_relative_to_dir(abs_path, self.get_config_dir())

def get_curv_paths(args: CurvCliArgs | Context | None = None) -> CurvPaths:
    """
    Get the paths commonly used in this build system, and track where CURV_ROOT_DIR was obtained from.
    """
    global curvpaths, _curvpaths_source

    # initialize curvpaths if it's not already initialized
    # (if we get called a second time with a non-None args, we re-initialize)
    if curvpaths is None or args is not None:

        # reset if it was previously set since now we're updating
        _curvroot_dir_source = None

        # extract args if we were passed a Context
        if isinstance(args, Context):
            temp_args = args.obj
        else:
            temp_args = args

        # if args was supplied, try it, but always fall back to the environment variable if set
        if temp_args is None or "curv_root_dir" not in temp_args:
            curv_root_dir = os.environ.get("CURV_ROOT_DIR")
            if curv_root_dir is not None and os.path.isdir(curv_root_dir):
                _curvroot_dir_source = ParameterSource.ENVIRONMENT
        else:
            curv_root_dir = temp_args.get("curv_root_dir", None)
            if curv_root_dir is not None and os.path.isdir(curv_root_dir):
                _curvroot_dir_source = ParameterSource.COMMANDLINE
            else:
                curv_root_dir = os.environ.get("CURV_ROOT_DIR")
                if curv_root_dir is not None and os.path.isdir(curv_root_dir):
                    _curvroot_dir_source = ParameterSource.ENVIRONMENT

        # fall back to git rev-parse to find repo root if unable to get CURV_ROOT_DIR from args or environment variable
        if not curv_root_dir:
            repo_root_dir = get_git_repo_root()
            curv_root_dir = get_curv_root_dir_from_repo_root(repo_root_dir)
            curv_root_dir = os.path.expanduser(str(curv_root_dir))

        # fail if we have not gotten a valid dir yet for CURV_ROOT_DIR
        if not os.path.isdir(curv_root_dir):
            get_console().print(f"[red]error:[/red] --curv-root-dir not found: {curv_root_dir}")
            raise SystemExit(1)
        else:
            # Default in this context means it was found through git-rev-parse
            _curvroot_dir_source = ParameterSource.DEFAULT

        curvpaths = CurvPaths(curv_root_dir)

    return curvpaths