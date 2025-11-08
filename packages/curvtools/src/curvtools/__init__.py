try:
    from ._version import __version__
except Exception:
    try:
        from importlib.metadata import version as _v
        __version__ = _v("curvtools")
    except Exception:
        __version__ = "0.0.0.dev0+gunknown"


from .version import (
    get_version_str as get_curvtools_version_str,
)

__all__ = [
    "get_curvtools_version_str",
]