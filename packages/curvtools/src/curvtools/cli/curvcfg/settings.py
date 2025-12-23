from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import entry_points, PackageNotFoundError
from pathlib import Path
from typing import Iterable

PROGRAM_NAME = "curvcfg"

# Python package name (import name)
PACKAGE_NAME: str = __package__.split(".")[0]  # "curvtools"

__all__ = [
    "PROGRAM_NAME",
    "PACKAGE_NAME",
]