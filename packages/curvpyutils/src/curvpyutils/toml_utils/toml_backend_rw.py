from __future__ import annotations
from typing import Any, Dict
import sys

# Global variable storing the toml backend that is loaded. This is set up the first
# time a TOML loader function is used.
_TOML_BACKEND = None

################################################################################
#
# Private TOML helper functions
#
################################################################################

def _init_toml_backend():
    global _TOML_BACKEND
    try:
        import tomllib  # noqa: F401 # type: ignore
        _TOML_BACKEND = "tomllib"
    except Exception:
        try:
            import tomli  # noqa: F401 # type: ignore
            _TOML_BACKEND = "tomli"
        except Exception:
            try:
                import toml  # noqa: F401 # type: ignore
                _TOML_BACKEND = "toml"
            except Exception:
                sys.stderr.write(
                    "Error: No TOML parser found. Install one of:\n"
                    "  pip install tomli tomli-w   (recommended)\n"
                    "  or\n"
                    "  pip install toml\n"
                )
                sys.exit(1)

def _load_toml_bytes(b: bytes) -> dict[str, Any]:
    """
    Dispatch to whichever TOML backend we found.

    Args:
        b: the bytes of a TOML file to load into a dictionary

    Returns:
        A dictionary that contains the parsed TOML data.
    """
    global _TOML_BACKEND
    if _TOML_BACKEND is None: _init_toml_backend()
    if _TOML_BACKEND == "tomllib":
        import tomllib  # type: ignore
        return tomllib.loads(b.decode("utf-8"))
    elif _TOML_BACKEND == "tomli":
        import tomli  # type: ignore
        return tomli.loads(b.decode("utf-8"))
    elif _TOML_BACKEND == "toml":
        import toml  # type: ignore
        return toml.loads(b.decode("utf-8"))
    else:
        raise RuntimeError("No TOML backend available")

################################################################################
#
# Public TOML helper functions
#
################################################################################

def dump_dict_to_toml_str(d: dict[str, Any]) -> str:
    """
    Dispatch to whichever TOML backend we found.

    Args:
        d: the dictionary to dump into a TOML string

    Returns:
        A TOML string that can be written to a .toml file.
    """
    global _TOML_BACKEND
    if _TOML_BACKEND is None: _init_toml_backend()
    if _TOML_BACKEND == "tomllib" or _TOML_BACKEND == "tomli":
        # tomllib and tomli are read-only, use tomli_w for writing
        import tomli_w  # type: ignore
        return tomli_w.dumps(d)
    elif _TOML_BACKEND == "toml":
        import toml  # type: ignore
        return toml.dumps(d)  # toml.dumps() returns str, not bytes
    else:
        raise RuntimeError("No TOML backend available")

def read_toml_file(path:str) -> Dict[str, Any]:
    global _TOML_BACKEND
    if _TOML_BACKEND is None: _init_toml_backend()
    with open(path, "rb") as f:
        data = _load_toml_bytes(f.read())
    return data

__all__ = ["dump_dict_to_toml_str", "read_toml_file"]
