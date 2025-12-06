from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable
import sys
from pathlib import Path
from typing import BinaryIO
from ._canonicalizer import canonicalize_toml_str

# Global variable storing the TOML backend object that is loaded.
# Initialized on first use.
_TOML_BACKEND: "TomlBackend | None" = None


@runtime_checkable
class TomlBackend(Protocol):
    def loads(self, s: str) -> Dict[str, Any]: ...
    def dumps(self, d: Dict[str, Any]) -> str: ...


################################################################################
#
# Private TOML helper functions
#
################################################################################


def _init_toml_backend() -> None:
    """
    Initialize the global TOML backend.

    Preference order:
      1. stdlib tomllib + tomli_w
      2. tomli + tomli_w
      3. toml
    """
    global _TOML_BACKEND
    if _TOML_BACKEND is not None:
        return

    # 1) Try stdlib tomllib (Python 3.11+) with tomli_w for writing
    try:
        import tomllib  # type: ignore[import]
        import tomli_w  # type: ignore[import]

        class _Backend:
            @staticmethod
            def loads(s: str) -> Dict[str, Any]:
                return tomllib.loads(s)

            @staticmethod
            def dumps(d: Dict[str, Any]) -> str:
                # tomli_w returns str
                return tomli_w.dumps(d)

        _TOML_BACKEND = _Backend()
        return
    except Exception:
        pass

    # 2) Try tomli + tomli_w
    try:
        import tomli  # type: ignore[import]
        import tomli_w  # type: ignore[import]

        class _Backend:
            @staticmethod
            def loads(s: str) -> Dict[str, Any]:
                return tomli.loads(s)

            @staticmethod
            def dumps(d: Dict[str, Any]) -> str:
                return tomli_w.dumps(d)

        _TOML_BACKEND = _Backend()
        return
    except Exception:
        pass

    # 3) Fallback: toml (read/write)
    try:
        import toml  # type: ignore[import]

        class _Backend:
            @staticmethod
            def loads(s: str) -> Dict[str, Any]:
                return toml.loads(s)

            @staticmethod
            def dumps(d: Dict[str, Any]) -> str:
                # toml.dumps returns str
                return toml.dumps(d)

        _TOML_BACKEND = _Backend()
        return
    except Exception:
        pass

    # Nothing found
    sys.stderr.write(
        "Error: No TOML parser found. Install one of:\n"
        "  pip install tomli tomli-w   (recommended)\n"
        "  or\n"
        "  pip install toml\n"
    )
    sys.exit(1)


def _ensure_backend() -> TomlBackend:
    global _TOML_BACKEND
    if _TOML_BACKEND is None:
        _init_toml_backend()
    # mypy/pyright: at this point it's definitely not None
    assert _TOML_BACKEND is not None
    return _TOML_BACKEND


def _load_toml_bytes(b: bytes) -> Dict[str, Any]:
    """
    Parse TOML from raw bytes into a dict.
    """
    backend = _ensure_backend()
    return backend.loads(b.decode("utf-8"))

################################################################################
#
# Public TOML helper functions
#
################################################################################


def dumps(d: Dict[str, Any], should_canonicalize: bool = False, should_sort_if_canonicalizing: bool = False) -> str:
    """
    Write a dict[str,Any] to toml format. Dispatch to whichever TOML backend 
    we found. Optionally canonicalize the TOML string if `taplo` or python 
    `tomli`/`toml` libraries are available.

    Args: 
        d: the dictionary to dump into a TOML string
        should_canonicalize: whether to canonicalize the TOML string using `taplo` 
        if available. If `False`, `should_sort_if_canonicalizing` is ignored.
        should_sort_if_canonicalizing: whether to sort the keys of the dictionary before 
        canonicalizing. If `False`, the keys are not sorted.
    Returns: 
        A TOML string that can be written to a .toml file. 
    """
    backend = _ensure_backend()
    s = backend.dumps(d)
    if should_canonicalize:
        s = canonicalize_toml_str(s, should_sort=should_sort_if_canonicalizing)
    return s


def loadf(path: str|Path) -> Dict[str, Any]:
    """
    Load a TOML file into a dict[str,Any]. Dispatch to whichever TOML backend 
    we find on this system.
    
    Args: 
        path: the path to the TOML file
    
    Returns: 
        A dictionary that can be used to read the TOML file.
    """
    if isinstance(path, Path): path = str(path) # type: ignore[assignment]
    with open(path, "rb") as f:
        data = _load_toml_bytes(f.read())
    return data

def load(f: BinaryIO) -> Dict[str, Any]:  # type: ignore[reportIncompatibleMethodOverride]
    """
    Load a TOML file from a file object opened in binary mode.
    
    Args: 
        f: the file object opened in binary mode
    
    Returns: 
        A dictionary that can be used to read the TOML file.
    """
    data = _load_toml_bytes(f.read())
    return data

def loads(s: str) -> Dict[str, Any]:
    """
    Load a TOML string into a dict[str,Any]. Dispatch to whichever TOML backend 
    we find on this system.
    
    Args: 
        s: the TOML string
    
    Returns: 
        A dictionary that can be used to read the TOML string.
    """
    backend = _ensure_backend()
    return backend.loads(s)

__all__ = [
    "dumps",
    "loadf",
    "loads",
]
