"""Version utilities."""

from typing import Tuple, Union

try:
    from ._version import __version__, __version_tuple__
except ImportError:
    __version__ = "0.0.0.dev0+g????????"
    __version_tuple__ = ("0", "0", "0", "dev0", "g????????")

def get_curvpyutils_version_str() -> str:
    """Get the Curv Python utilities version string."""
    return __version__

def get_curvpyutils_version_tuple() -> Tuple[int,int,int]:
    """Get the Curv Python utilities version tuple."""
    return __version_tuple__[:3]

__all__ = [
    "get_curvpyutils_version_str",
    "get_curvpyutils_version_tuple",
]