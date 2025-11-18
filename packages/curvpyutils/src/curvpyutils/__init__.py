"""Curv Python shared utilities package."""

try:
    from ._version import __version__
except Exception:
    try:
        from importlib.metadata import version as _v
        __version__ = _v("curvpyutils")
    except Exception:
        __version__ = "0.0.0.dev0+gunknown"

__all__ = [
    "cli_util",
    "logging",
    "test_helpers",
    "colors",
    "file_utils",
    "multi_progress",
    "shellutils",
    "system",
    "str_utils",
    "toml_utils",
    "version_utils",
]
