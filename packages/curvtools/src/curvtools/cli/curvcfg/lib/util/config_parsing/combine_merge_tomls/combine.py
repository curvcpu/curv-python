"""
Combines (concatenate) or overlays (merge) 1 or more toml's style files into a single dict[str, Any] that 
can be serialzed to a merged_<name>.toml style file.
"""

from __future__ import annotations
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Iterable

try:                         # Python 3.11+
    import tomllib as tlib   # type: ignore[attr-defined]
except ModuleNotFoundError:  # Python <= 3.10
    import tomli as tlib     # type: ignore[import-untyped]


def _deep_merge(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Deep merge two TOML trees: override wins; tables are merged recursively."""
    for k, v in override.items():
        if isinstance(v, Mapping) and isinstance(base.get(k), Mapping):
            # merge into a shallow copy of the existing table
            base[k] = _deep_merge(dict(base[k]), v)
        else:
            # scalars / arrays / mismatched types: override replaces
            base[k] = v
    return base


def _concatenate(base: dict[str, Any], other: Mapping[str, Any]) -> dict[str, Any]:
    """
    Union-style concatenate of two TOML trees.

    - Keys that are only present in ``other`` are added to ``base``.
    - If a key exists in both:
      - When both values are mappings, they are recursively concatenated with the
        same union semantics.
      - Otherwise, the two values must be equal (using normal Python equality),
        or a KeyError is raised.
    """
    for k, v in other.items():
        if k not in base:
            base[k] = v
            continue

        existing = base[k]

        # If both sides are mappings, recurse with union semantics.
        if isinstance(existing, Mapping) and isinstance(v, Mapping):
            # Reuse existing mapping when possible; fall back to a plain dict.
            if isinstance(existing, dict):
                base[k] = _concatenate(existing, v)
            else:
                base[k] = _concatenate(dict(existing), v)
            continue

        # Non-mapping (or mismatched types): must be exactly equal.
        if existing != v:
            raise KeyError(
                f"Conflicting values for key {k!r}: {existing!r} vs {v!r}"
            )
        # If equal, keep the existing value.

    return base


def _deep_sort(obj: Any) -> Any:
    """Recursively sort mapping keys; leave values and list order otherwise."""
    if isinstance(obj, Mapping):
        return {k: _deep_sort(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_deep_sort(x) for x in obj]
    return obj


def merge_tomls(paths: Iterable[str | Path]) -> dict[str, Any]:
    """
    Deep-merge multiple TOML files and sort the result by key.

    Earlier files are the base; later files override or add to them. When the same
    key exists in multiple files, the value from the later file wins. Nested tables
    are merged recursively.

    Args:
        paths: the list of paths to the TOML files to merge

    Returns:
        A dictionary of the merged TOMLs, sorted by key
    """
    final_dict: dict[str, Any] = {}

    for p in paths:
        with open(p, "rb") as f:
            data = tlib.load(f)
        final_dict = _deep_merge(final_dict, data)

    return _deep_sort(final_dict)


def combine_tomls(paths: Iterable[str | Path]) -> dict[str, Any]:
    """
    Combine multiple TOML files into a single dict and sort the result by key.

    All files are combined into a single dict without any notion of later files
    overriding key-value pairs from earlier files. A KeyError is raised if any
    TOML key is present in multiple files, unless both values for that key are
    identical (recursive comparison if the value is a complex type). If the values
    are identical, no error is raised.

    Args:
        paths: the list of paths to the TOML files to combine

    Returns:
        A dictionary of the combined TOMLs, sorted by key
    """
    final_dict: dict[str, Any] = {}

    for p in paths:
        with open(p, "rb") as f:
            data = tlib.load(f)
        final_dict = _concatenate(final_dict, data)

    return _deep_sort(final_dict)

__all__ = ["merge_tomls", "combine_tomls"]

