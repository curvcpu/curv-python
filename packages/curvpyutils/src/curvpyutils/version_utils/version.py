"""Version utilities."""

from .._version import __version__

def get_version_str(full_version_str: str = __version__, short_version: bool = True) -> str:
    """Get the short package version string (major.minor.patch) or 
    long package version string (major.minor.patch.prerelease+build)."""
    if not short_version:
        return full_version_str
    else:
        return '.'.join(full_version_str.split('.')[:3])

__all__ = [
    "get_version_str",
]