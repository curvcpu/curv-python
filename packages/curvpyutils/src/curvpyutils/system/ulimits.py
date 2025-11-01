import math
import resource
import sys
from typing import Tuple, Union


Num = Union[int, float]


def _norm(value: int) -> Num:
    return math.inf if value == resource.RLIM_INFINITY else value


def raise_recursion_limit(limit: int = 10_000) -> int:
    """Raise Python's recursion limit and return the new value."""

    sys.setrecursionlimit(limit)
    return sys.getrecursionlimit()


def get_recursion_limit() -> int:
    """Return the current Python recursion limit."""

    return sys.getrecursionlimit()


def raise_stack_limit(limit: int = 512 * 1024 * 1024) -> Tuple[Num, Num]:
    """Raise the soft stack size limit up to ``limit`` and return the result."""

    _soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
    new_soft = limit if hard == resource.RLIM_INFINITY else min(limit, hard)
    resource.setrlimit(resource.RLIMIT_STACK, (new_soft, hard))
    soft, new_hard = resource.getrlimit(resource.RLIMIT_STACK)
    return _norm(soft), _norm(new_hard)


def get_stack_limit() -> Tuple[Num, Num]:
    """Return the current soft and hard stack limits."""

    soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
    return _norm(soft), _norm(hard)


def get_max_memory_kb() -> int:
    """Return the maximum resident set size recorded for this process."""

    usage = resource.getrusage(resource.RUSAGE_SELF)
    max_rss = usage.ru_maxrss
    if sys.platform.startswith("linux"):
        return max_rss
    if sys.platform == "darwin":
        return int(max_rss / 1024)
    return int(max_rss / 1024)

