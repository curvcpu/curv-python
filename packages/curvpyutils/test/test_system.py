"""Unit tests for curvpyutils.system."""

from typing import Tuple, Union

import pytest

from curvpyutils.system import (
    get_max_memory_kb,
    get_nprocs,
    get_recursion_limit,
    get_stack_limit,
    raise_recursion_limit,
    raise_stack_limit,
)

pytestmark = [pytest.mark.unit]

Num = Union[int, float]


class TestSystem:
    def test_get_nprocs(self):
        nprocs = get_nprocs()
        assert nprocs > 0

    def test_get_max_memory_kb(self):
        max_memory_kb = get_max_memory_kb()
        assert max_memory_kb > 0

    def test_raise_recursion_limit(self):
        recursion_limit = raise_recursion_limit(10_000)
        assert recursion_limit > 1_000

    def test_raise_stack_limit(self):
        # Get initial limits
        initial_soft, initial_hard = get_stack_limit()

        # Try to raise the limit (may not succeed on all platforms like macOS)
        stack_limit: Tuple[Num, Num] = raise_stack_limit(512 * 1024 * 1024)

        # The function should return valid limits
        assert stack_limit[0] > 0
        assert stack_limit[1] >= stack_limit[0]

        # The soft limit should be at least as high as it was initially
        # (it might be higher if the raise succeeded, or same if it didn't)
        assert stack_limit[0] >= initial_soft

    def test_get_recursion_limit(self):
        recursion_limit = get_recursion_limit()
        assert recursion_limit > 10

    def test_get_stack_limit(self):
        stack_limit = get_stack_limit()
        assert stack_limit[0] > 0
        assert stack_limit[1] >= stack_limit[0]

