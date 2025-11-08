try:
    from ._version import __version__
except Exception:
    try:
        from importlib.metadata import version as _v
        __version__ = _v("curv")
    except Exception:
        __version__ = "0.0.0.dev0+gunknown"
        
from .version import (
    get_version_str as get_curv_version_str,
)

__all__ = [
    "get_curv_version_str",
]