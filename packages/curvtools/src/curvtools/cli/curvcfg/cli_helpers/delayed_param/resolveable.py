from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Callable, Generic, Optional, TypeVar
from curvtools.cli.curvcfg.lib.curv_paths import CurvPaths

T = TypeVar("T")

Resolver = Callable[[CurvPaths], T]


@dataclass
class Resolvable(Generic[T]):
    """
    Either a concrete T, or a resolver CurvPaths -> T that we call later.

    `raw` is the original CLI string (useful for error messages / logging).
    """
    _value: Optional[T] = None
    _resolver: Optional[Resolver] = None
    raw: Optional[str] = None

    def is_resolved(self) -> bool:
        return self._value is not None

    def resolve(self, curvpaths: CurvPaths) -> T:
        if self._value is not None:
            return self._value
        if self._resolver is None:
            raise RuntimeError("Resolvable has neither value nor resolver")
        self._value = self._resolver(curvpaths)
        self._resolver = None
        return self._value

    @property
    def value(self) -> T:
        if self._value is None:
            raise RuntimeError("Resolvable.value accessed before resolve()")
        return self._value