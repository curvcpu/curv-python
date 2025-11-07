"""Version utilities."""

from typing import Tuple, Union

try:
    from ._version import __version__, __version_tuple__
except ImportError:
    __version__ = "0.0.0.dev0+g????????"
    __version_tuple__ = ("0", "0", "0", "dev0", "g????????")

def get_full_version_str() -> str:
    """Get the long package version string (major.minor.patch.prerelease+build)."""
    return __version__

def get_version_str() -> str:
    """Get the package version string (major.minor.patch)."""
    return '.'.join(str(v) for v in __version_tuple__[:3])

__all__ = [
    "get_full_version_str",
    "get_version_str",
]