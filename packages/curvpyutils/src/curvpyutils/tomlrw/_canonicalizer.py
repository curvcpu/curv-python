from __future__ import annotations

"""
Simplified canonicalizer func that uses `taplo` if available on the system's PATH, 
otherwise falls back to Python `tomli` or `toml` libraries.

Name:
    canonicalize_toml_str(str,bool) -> str

Args:
    toml_str: the TOML string to canonicalize
    should_sort: whether to sort keys when canonicalizing; defaults to False

Returns:
    The canonicalized TOML string
"""

import subprocess
from typing import Any, Dict
from collections import OrderedDict

from curvpyutils.shellutils import Which

# These are taplo-specific arguments that could be arguments to the function 
# in the future, but for now are hardcoded. (Python fallback cannot do any of this.)
TAPLO_ALIGN_ENTRIES = True
TAPLO_ARRAY_TRAILING_COMMA = True
TAPLO_ARRAY_AUTO_EXPAND = True
TAPLO_ARRAY_AUTO_COLLAPSE = False
TAPLO_COMPACT_ARRAYS = False


def _run_taplo_on_stdin(toml_str: str, should_sort: bool = False) -> str:
    """
    Run taplo to canonicalize a TOML string via stdin/stdout.

    Args:
        toml_str: the TOML contents to canonicalize
        should_sort: whether to sort keys when canonicalizing; defaults to False

    IMPORTANT: taplo can go berserk and reformat everything recursively under
    the current working directory if invoked with glob patterns or directories,
    so this helper *never* passes paths or globs to taplo. Instead, it always
    sends the TOML via stdin and uses "-" as the only file argument.
    """
    try:
        taplo_cmd = Which("taplo", on_missing_action=Which.OnMissingAction.RAISE)()
    except FileNotFoundError:
        # Propagate to caller; they'll decide to fall back to Python.
        raise

    cmd = [
        str(taplo_cmd),
        "fmt",
        "-o",
        f"align_entries={str(TAPLO_ALIGN_ENTRIES).lower()}",
        "-o",
        f"array_trailing_comma={str(TAPLO_ARRAY_TRAILING_COMMA).lower()}",
        "-o",
        f"reorder_keys={str(should_sort).lower()}",
        "-o",
        f"array_auto_expand={str(TAPLO_ARRAY_AUTO_EXPAND).lower()}",
        "-o",
        f"array_auto_collapse={str(TAPLO_ARRAY_AUTO_COLLAPSE).lower()}",
        "-o",
        f"compact_arrays={str(TAPLO_COMPACT_ARRAYS).lower()}",
        "-",  # read TOML from stdin, write canonical TOML to stdout
    ]

    try:
        proc = subprocess.run(
            cmd,
            input=toml_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"taplo returned non-zero (exit code {e.returncode}): {e.stderr}"
        ) from e

    return proc.stdout


def _python_toml_loads(s: str) -> Dict[str, Any]:
    """
    Best-effort TOML loader using Python libraries:
      1. stdlib tomllib
      2. tomli
      3. toml
    """
    try:
        import tomllib  # type: ignore[import]

        return tomllib.loads(s)
    except Exception:
        pass

    try:
        import tomli  # type: ignore[import]

        return tomli.loads(s)
    except Exception:
        pass

    try:
        import toml  # type: ignore[import]

        return toml.loads(s)
    except Exception:
        pass

    raise RuntimeError(
        "No TOML parser available for Python fallback. "
        "Install one of: tomli, tomli-w, or toml."
    )


def _python_toml_dumps(d: Dict[str, Any]) -> str:
    """
    Best-effort TOML dumper using Python libraries:
      1. tomli_w
      2. toml
    """
    try:
        import tomli_w  # type: ignore[import]

        return tomli_w.dumps(d)
    except Exception:
        pass

    try:
        import toml  # type: ignore[import]

        return toml.dumps(d)
    except Exception:
        pass

    raise RuntimeError(
        "No TOML writer available for Python fallback. "
        "Install tomli-w or toml."
    )


def _sort_obj(x: Any) -> Any:
    """
    Recursively sort dict keys (lexicographically) and recurse into lists.
    """
    if isinstance(x, dict):
        return OrderedDict(
            (k, _sort_obj(v)) for k, v in sorted(x.items(), key=lambda kv: kv[0])
        )
    if isinstance(x, list):
        return [_sort_obj(v) for v in x]
    return x


def _canonicalize_with_python_str(toml_str: str, should_sort: bool) -> str:
    """
    Canonicalize TOML using Python libraries:
      - parse
      - optionally sort keys recursively
      - dump back to TOML
    """
    data = _python_toml_loads(toml_str)

    if should_sort:
        data = _sort_obj(data)

    return _python_toml_dumps(data)

################################################################################
#
# Public canonicalize_toml_str() function
#
################################################################################

def canonicalize_toml_str(toml_str: str, should_sort: bool = False) -> str:
    """
    Canonicalize a TOML string using an external taplo CLI if available,
    otherwise fall back to a Python TOML implementation.

    - Sends `toml_str` to `taplo fmt` via stdin and captures stdout.
    - If taplo is unavailable, uses Python TOML libs to re-emit the string.
    - Optionally sorts keys when `should_sort` is True (both taplo and Python
      fallback receive the same `should_sort` semantics).
    - Does not create any temporary files.
    - Returns the canonicalized TOML as a string.
    """
    try:
        return _run_taplo_on_stdin(toml_str, should_sort=should_sort)
    except FileNotFoundError:
        # No taplo available; fall back to Python.
        return _canonicalize_with_python_str(toml_str, should_sort=should_sort)


__all__ = ["canonicalize_toml_str"]