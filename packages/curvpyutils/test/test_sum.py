import pytest

from curvpyutils.adder.add import sum

pytestmark = [pytest.mark.unit]


def test_sum():
    assert sum(5, 10) == 15
