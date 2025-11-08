from . import __version__
from curvpyutils.version_utils import get_version_str as gvs

def get_version_str(short_version: bool = True) -> str:
    """Get the short package version string (major.minor.patch) or 
    long package version string (major.minor.patch.prerelease+build)."""
    return gvs(__version__, short_version)

__all__ = [
    "get_version_str",
]