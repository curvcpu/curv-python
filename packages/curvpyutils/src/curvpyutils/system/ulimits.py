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

    soft, hard = resource.getrlimit(resource.RLIMIT_STACK)

    # Never try to exceed the hard limit
    if hard != resource.RLIM_INFINITY:
        limit = min(limit, hard)

    # Only try to raise if the requested limit is higher than current soft limit
    if limit <= soft:
        return _norm(soft), _norm(hard)

    # On macOS and some systems, we might not be able to set arbitrarily high limits
    # Try progressively smaller limits until we succeed
    try:
        resource.setrlimit(resource.RLIMIT_STACK, (limit, hard))
    except ValueError:
        # If the requested limit fails, try with current soft limit (no change)
        # This handles cases where the system doesn't allow the requested limit
        pass

    # Return the actual current limits after any attempted changes
    soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
    return _norm(soft), _norm(hard)


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

