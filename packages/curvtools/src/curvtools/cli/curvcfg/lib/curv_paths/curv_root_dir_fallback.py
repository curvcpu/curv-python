from pathlib import Path
from typing import Optional
from curvpyutils.file_utils.repo_utils import get_git_repo_root
from .curvpaths_temporary import get_curv_root_dir_from_repo_root

def try_get_curvrootdir_git_fallback() -> Optional[Path]:
    curvrootdir_git_fallback = Path(get_curv_root_dir_from_repo_root(get_git_repo_root())
        ) if get_git_repo_root() else None
    if curvrootdir_git_fallback is not None:
        if (curvrootdir_git_fallback / ".git").is_dir():
            with open(curvrootdir_git_fallback / ".git" / "config", "r") as f:
                config = f.read()
                return curvrootdir_git_fallback if "curv/curvcpu" in config else None
    return None
