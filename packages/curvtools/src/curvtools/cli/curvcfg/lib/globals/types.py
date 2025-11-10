from typing import Dict, Union
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import FsPathType
from pathlib import Path

CurvCliArgs = Dict[str, Union[str, bool, None, int, FsPathType, Path]]