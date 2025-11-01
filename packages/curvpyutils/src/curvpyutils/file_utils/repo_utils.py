import os
import subprocess
from pathlib import Path
from typing import Optional


def get_git_repo_root(cwd: Optional[str] = None) -> Optional[str]:
    """Return the absolute path to the git repository root for ``cwd``."""

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            check=True,
            capture_output=True,
            cwd=cwd,
        )
    except subprocess.CalledProcessError:
        return None

    return result.stdout.strip() if result.stdout else None


def is_path_writeable(path: str | Path) -> bool:
    """Return ``True`` if ``path`` is within a writable directory."""

    directory = os.path.dirname(str(path)) or "."
    return os.path.isdir(directory) and os.access(directory, os.W_OK)


def make_repo_root_relpath_into_abs(
    rel_to_repo_root_path: str | Path, repo_root_abspath: Optional[str] = None
) -> str:
    """Resolve ``rel_to_repo_root_path`` against ``repo_root_abspath`` if provided."""

    path = Path(rel_to_repo_root_path)
    if path.is_absolute() or not repo_root_abspath:
        return str(path.resolve())
    return str((Path(repo_root_abspath) / path).resolve())

