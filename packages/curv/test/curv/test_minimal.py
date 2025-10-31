import pytest

pytestmark = [pytest.mark.unit]


def test_trivial():
    assert 2 + 2 == 4
