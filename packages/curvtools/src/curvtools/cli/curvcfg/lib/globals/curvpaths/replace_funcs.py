"""
Compatibility wrapper re-exporting the match/replace helpers from the
new ``lib.curv_paths`` package layout.
"""

from curvtools.cli.curvcfg.lib.curv_paths.replace_funcs import (
    match_vars,
    replace_vars,
)

__all__ = [
    "match_vars",
    "replace_vars",
]

