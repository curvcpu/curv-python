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
from curvtools.cli.curvcfg.lib.globals.curvpaths_temporary import get_curv_root_dir_from_repo_root

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
        if merged_toml is not None:
            self.cfg_values = get_config_values(config=merged_toml, schema=None, is_combined_toml=True)
        else:
            self.cfg_values = None
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
        self.cfg_values = get_config_values(
            config=merged_toml, 
            schema=None, 
            is_combined_toml=True
        ) if merged_toml is not None else self.cfg_values
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

        detailed_error_msg = (
            f"The program was unable to get " 
            "a valid CURV_ROOT_DIR from --curv-root-dir argument, CURV_ROOT_DIR environment variable, or using git "
            "repository root based on the current directory. " 
            "The program cannot function unless a valid CURV_ROOT_DIR is provided somehow. \n\n"
            "(Hint: try setting CURV_ROOT_DIR environment variable in your shell's rc file,"
            "or cd'ing any directory under the curvcpu/curv repo root.)"
        )

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
            try:
                repo_root_dir = get_git_repo_root()
                repo_root_dir = os.path.expanduser(str(repo_root_dir))
                curv_root_dir = get_curv_root_dir_from_repo_root(repo_root_dir)
            except Exception as e:
                console.print(f"[red]error:[/red] {os.path.basename(__file__)}:{inspect.currentframe().f_lineno}: unable to get CURV_ROOT_DIR from git rev-parse\n\n{detailed_error_msg}")
                raise SystemExit(1)

        # fail if we have not gotten a valid dir yet for CURV_ROOT_DIR
        if not os.path.isdir(curv_root_dir):
            console.print(f"[red]error:[/red] {os.path.basename(__file__)}:{inspect.currentframe().f_lineno}: --curv-root-dir not found: {curv_root_dir}\n\n{detailed_error_msg}")
            raise SystemExit(1)
        else:
            # Default in this context means it was found through git-rev-parse
            _curvroot_dir_source = ParameterSource.DEFAULT

        kwargs = {'curv_root_dir': curv_root_dir}
        if temp_args is not None and "build_dir" in temp_args:
            kwargs['build_dir'] = temp_args.get("build_dir")
        if temp_args is not None and "profile" in temp_args:
            kwargs['profile'] = temp_args.get("profile")
        if temp_args is not None and "board" in temp_args:
            kwargs['board'] = temp_args.get("board")
        if temp_args is not None and "device" in temp_args:
            kwargs['device'] = temp_args.get("device")
        if temp_args is not None and "merged_toml" in temp_args:
            kwargs['merged_toml'] = temp_args.get("merged_toml")
        if curvpaths is not None:
            curvpaths.update_and_refresh(**kwargs)
        else:
            curvpaths = CurvPaths(**kwargs)

    return curvpaths