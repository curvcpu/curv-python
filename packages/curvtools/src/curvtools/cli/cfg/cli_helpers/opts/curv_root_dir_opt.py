import os
from typing import Optional
from curvpyutils.file_utils.repo_utils import get_git_repo_root
import click
from click.shell_completion import CompletionItem

def _list_all_repo_subdirs(repo_root: Optional[str], prefix: Optional[str] = None) -> list[str]:
    """Return all directories under repo_root (recursively), as absolute paths, sorted.

    Includes repo_root itself; only subdirectories are returned.
    If prefix is provided, only subdirectories that start with prefix are returned.
    """
    if not repo_root or not os.path.isdir(repo_root):
        return []
    abs_root = os.path.abspath(repo_root)
    subdirs: list[str] = []
    for dirpath, dirnames, _filenames in os.walk(abs_root):
        if prefix and os.path.isabs(prefix) and not dirpath.startswith(os.path.abspath(prefix)):
            continue
        subdirs.append(dirpath + "/")
    subdirs.sort()
    return subdirs

def shell_complete_curv_root_dir(ctx: click.Context, param: click.Parameter, incomplete: str) -> list[CompletionItem]:
    items: list[CompletionItem] = []

    # list every directory under the repo root that matches incomplete as an absolute dir prefix
    if incomplete and os.path.isabs(incomplete):
        repo_root = get_git_repo_root()
        subdirs: list[str] = _list_all_repo_subdirs(repo_root, incomplete)
        for subdir in subdirs:
            items.append(CompletionItem(subdir, type="plain", help=subdir))
    else:
        items.append(CompletionItem(None, type="dir", help=f"CURV_ROOT_DIR"))
    return items
