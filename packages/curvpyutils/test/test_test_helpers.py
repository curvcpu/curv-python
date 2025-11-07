"""Unit tests for curvpyutils.test_helpers."""

from pathlib import Path
from typing import Tuple, Union

import pytest

from curvpyutils import test_helpers

pytestmark = [pytest.mark.unit]

class TestCompareFiles:
    def test_compare_files_same(self):
        test_file = Path(__file__).parent / "test_vectors" / "input" / "comparison_same.txt"
        expected_file = Path(__file__).parent / "test_vectors" / "expected" / "comparison_same.txt"
        assert test_helpers.compare_files(test_file, expected_file)

    def test_compare_files_different(self):
        test_file = Path(__file__).parent / "test_vectors" / "input" / "comparison_different.txt"
        expected_file = Path(__file__).parent / "test_vectors" / "expected" / "comparison_different.txt"
        cmp_result = test_helpers.compare_files(test_file, expected_file)
        assert cmp_result is False