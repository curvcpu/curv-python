# curvtools/settings.py
from __future__ import annotations

from importlib.metadata import entry_points, PackageNotFoundError
from typing import Iterable

PROGRAM_NAME = "curvcfg"

# Python package name (import name)
PACKAGE_NAME: str = __package__.split(".")[0]  # "curvtools"

__all__ = [
    "PROGRAM_NAME",
    "PACKAGE_NAME",
]