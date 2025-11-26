import os
from pathlib import Path
from typing import Dict, Union, Optional, Any
from curvtools.cli.curvcfg.lib.globals.console import console
from curvpyutils.file_utils.repo_utils import get_git_repo_root
from dotenv import dotenv_values
from curvtools.cli.curvcfg.lib.globals.types import CurvCliArgs
from click import Context
from click.core import ParameterSource
from curvtools.cli.curvcfg.lib.globals.constants import PATHS_RAW_ENV_FILE_REL_PATH
import inspect
from curvtools.cli.curvcfg.lib.util import get_config_values
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import FsPathType
from .curvpath import CurvPath
from ..util.cfgvalue import CfgValues, CfgValue

curvpaths: Optional[Dict[str, CurvPath]] = None
_curvroot_dir_source: Optional[ParameterSource] = None

class CurvPaths(dict[str, CurvPath]):
    def __init__(self, curv_root_dir: str|Path, build_dir: str | None = None, profile: str | None = None, board: str | None = None, device: str | None = None, merged_toml: [FsPathType | dict[str, Any]]= None):
        super().__init__()
        self.curv_root_dir = Path(curv_root_dir).resolve() if curv_root_dir is not None else None
        self.env_file = self.curv_root_dir / PATHS_RAW_ENV_FILE_REL_PATH
        self.build_dir = Path(build_dir).resolve() if build_dir is not None else None
        self.profile = profile
        self.board = board
        self.device = device
        self.cfg_values = None
        if merged_toml is not None:
            if isinstance(merged_toml, dict[str, CfgValue]):
                self.cfg_values = CfgValues(vals=merged_toml)
            elif isinstance(merged_toml, (str, Path, FsPathType, dict[str, Any])):
                self.cfg_values = get_config_values(
                    config=merged_toml, 
                    schema=None, 
                    is_combined_toml=True)
            else:
                raise ValueError(f"merged_toml must be a dictionary of CfgValue objects, a string, a path, or a FsPathType, but got {type(merged_toml)}")
        self._refresh_from_path_env_file()
        
    def _refresh_from_path_env_file(self):
        """
        Read a path_raw.env file and return a dictionary of the variables with their values interpreted where possible.
        """
        env_values_uninterpolated = dotenv_values(self.env_file, interpolate=False)
        env_values = dotenv_values(self.env_file)

        # now replace and $(VAR_NAME) with the value of VAR_NAME
        replacement_vals = { 
            'PROFILE': self.profile, 
            'BOARD': self.board, 
            'DEVICE': self.device,
            'BUILD_DIR': self.build_dir, 
            'CURV_ROOT_DIR': self.curv_root_dir,
        }
        if self.cfg_values is not None:
            for k, v in self.cfg_values.items():
                replacement_vals[k] = str(v)
        self.clear()
        for k, v in env_values.items():
            if v is None:
                continue
            new_value = CurvPath(
                path=v, 
                PROFILE=self.profile, 
                BOARD=self.board, 
                DEVICE=self.device,
                BUILD_DIR=self.build_dir, 
                CURV_ROOT_DIR=self.curv_root_dir, 
                cfgvalues=self.cfg_values,
                uninterpolated_value_info=(
                    env_values_uninterpolated.get(k, None),
                    env_values_uninterpolated
                )
            )
            self[k] = new_value
    
    def update_and_refresh(self, profile: str | None = None, board: str | None = None, device: str | None = None, build_dir: str | None = None, curv_root_dir: str | None = None, merged_toml: FsPathType | dict[str, Any] | None = None) -> None:
        """
        Update the paths and re-read the path_raw.env file.
        """
        self.profile = profile if profile is not None else self.profile 
        self.board = board if board is not None else self.board 
        self.device = device if device is not None else self.device
        self.build_dir = Path(build_dir).resolve() if build_dir is not None else self.build_dir
        self.curv_root_dir = Path(curv_root_dir).resolve() if curv_root_dir is not None else self.curv_root_dir
        if merged_toml is not None:
            if isinstance(merged_toml, dict[str, CfgValue]):
                self.cfg_values.update(merged_toml)
            elif isinstance(merged_toml, (str, Path, FsPathType)):
                self.cfg_values.update(get_config_values(
                    config=merged_toml, 
                    schema=None, 
                    is_combined_toml=True))
        self._refresh_from_path_env_file()

    def __str__(self):
        s = ""
        for k,v in self.items():
            s += f"{k}: {v}\n"
        s = s[:-1]
        return s

    def get_config_dir(self, add_trailing_slash: bool = False) -> str:
        return self["CURV_CONFIG_DIR"].to_str(add_trailing_slash=add_trailing_slash)
    def get_curv_root_dir(self, add_trailing_slash: bool = False) -> str:
        return CurvPath._add_trailing_slash(str(self.curv_root_dir)) if add_trailing_slash else str(self.curv_root_dir)
    def get_repo_dir(self, add_trailing_slash: bool = False) -> str:
        from curvtools.cli.curvcfg.lib.curvpaths.curvpaths_temporary import get_curv_root_dir_from_repo_root
        repo_root_dir = Path(get_curv_root_dir_from_repo_root(self.curv_root_dir, invert=True)).resolve()
        return CurvPath._add_trailing_slash(str(repo_root_dir)) if add_trailing_slash else str(repo_root_dir)

    @staticmethod
    def _try_make_relative_to_dir(path: str|Path, dir: str|Path) -> str:
        """
        Try to make any path into a path relative to a directory.
        If the path is not relative to the directory, return the path as an absolute path.
        """
        # Convert both paths to absolute paths
        p = Path(path).resolve()
        d = Path(dir).resolve()
        try:
            return str(p.relative_to(d))
        except ValueError:
            return str(p)

    @staticmethod
    def mk_rel_to_cwd(path: str|Path) -> str:
        """
        Try to make any path into a path relative to the current working directory.
        If the path is not relative to the current working directory, return the path as an absolute path.

        If the path is not already an absolute path, it will be absoluteized relative to the current 
        working directory.
        """
        p = Path(path).resolve()
        cwd = Path.cwd()
        try:
            return str(p.relative_to(cwd))
        except ValueError:
            return str(p)

    def mk_rel_to_curv_root(self, path: str|Path) -> str:
        """
        Try to make any path into a path relative to the curv root dir.
        If the path is not relative to the curv root dir, return the path as an absolute path.
        """
        return CurvPaths._try_make_relative_to_dir(path, self.get_curv_root_dir())

    def mk_rel_to_curv_config_dir(self, path: str|Path) -> str:
        """
        Try to make any path into a path relative to the curv config dir.
        If the path is not relative to the curv config dir, return the path as an absolute path.

        If the path is not already an absolute path, it will be absoluteized relative to the current 
        working directory.
        """
        return CurvPaths._try_make_relative_to_dir(path, self.get_config_dir())

def get_curv_paths(ctx: Context) -> CurvPaths:
    """
    Get the paths commonly used in this build system, and track where CURV_ROOT_DIR was obtained from.
    """
    global curvpaths, _curvpaths_source

    # initialize curvpaths if it's not already initialized
    # (if we get called a second time with a non-None args, we re-initialize)
    if curvpaths is None or ctx is not None:
        detailed_error_msg = (
            f"The program was unable to get " 
            "a valid CURV_ROOT_DIR from --curv-root-dir argument, CURV_ROOT_DIR environment variable, or using git "
            "repository root based on the current directory. " 
            "The program cannot function unless a valid CURV_ROOT_DIR is provided somehow. \n\n"
            "(Hint: try setting CURV_ROOT_DIR environment variable in your shell's rc file,"
            "or cd'ing any directory under the curvcpu/curv repo root.)"
        )

        curv_root_dir = ctx.obj.get("curv_root_dir", None)
        _curvroot_dir_source = ctx.get_parameter_source("curv_root_dir")

        kwargs = {'curv_root_dir': curv_root_dir}
        kwargs['build_dir'] = ctx.params.get("build_dir", None)
        kwargs['profile'] = ctx.params.get("profile", None)
        kwargs['board'] = ctx.params.get("board", None)
        kwargs['device'] = ctx.params.get("device", None)
        kwargs['merged_toml'] = ctx.params.get("merged_toml", None)
        if curvpaths is None:
            curvpaths = CurvPaths(**kwargs)
        else:
            curvpaths.update_and_refresh(**kwargs)

    return curvpaths
