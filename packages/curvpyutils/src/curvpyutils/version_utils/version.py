"""Version utilities."""

from .._version import __version__

def get_version_str(full_version_str: str = __version__, short_version: bool = True) -> str:
    """Get the short package version string (major.minor.patch) or 
    long package version string (major.minor.patch.prerelease+build)."""
    if short_version:
        return __version__
    else:
        return '.'.join(__version__.split('.')[:3])

__all__ = [
    "get_version_str",
]