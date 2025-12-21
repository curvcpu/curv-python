"""
Compatibility layer to keep legacy imports working while the curv paths
modules live under ``curvtools.cli.curvcfg.lib.curv_paths``.
"""

from curvtools.cli.curvcfg.lib.curv_paths import (
    CurvContext,
    CurvPath,
    CurvPaths,
    get_curv_paths,
    try_get_curvrootdir_git_fallback,
)

__all__ = [
    "CurvContext",
    "CurvPath",
    "CurvPaths",
    "get_curv_paths",
    "try_get_curvrootdir_git_fallback",
]

