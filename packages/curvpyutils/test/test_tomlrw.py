from __future__ import annotations
import os
import tempfile
from pathlib import Path

import pytest
pytestmark = [pytest.mark.unit]

import curvpyutils.tomlrw as tomlrw

class TestTomlRw:
    def test_dumps(self):
        d = {"a": 1, "b": 2}
        s = tomlrw.dumps(d)
        assert s == "a = 1\nb = 2\n"

    @staticmethod
    def _to_stripped_lines_list(s: str) -> list[str]:
        lines = s.split("\n")
        lines = [line.strip() for line in lines if line.strip()]
        return lines

    def test_dumps_canonicalize(self):
        d = {"a": 1, "b": [1, 2, 3]}
        s = tomlrw.dumps(d, should_canonicalize=True)
        expected = """
a = 1
b = [
  1,
  2,
  3,
]
"""
        s_lines = TestTomlRw._to_stripped_lines_list(s)
        expected_lines = TestTomlRw._to_stripped_lines_list(expected)
        assert len(s_lines) == len(expected_lines)
        for s_line, expected_line in zip(s_lines, expected_lines):
            assert s_line == expected_line

    @pytest.mark.parametrize("sort", [True, False])
    def test_dumps_sort_if_canonicalizing(self, sort: bool):
        d = {"b": 2, "a": 1}
        s = tomlrw.dumps(d, should_canonicalize=sort, should_sort_if_canonicalizing=sort)
        expected = "a = 1\nb = 2\n" if sort else "b = 2\na = 1\n"
        s_lines = TestTomlRw._to_stripped_lines_list(s)
        expected_lines = TestTomlRw._to_stripped_lines_list(expected)
        assert len(s_lines) == len(expected_lines)
        for s_line, expected_line in zip(s_lines, expected_lines):
            assert s_line == expected_line

    def test_loadf(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.toml")
            with open(path, "w") as f:
                f.write("a = 1\nb = 2\n")
            
            d = tomlrw.loadf(path)
            assert d == {"a": 1, "b": 2}

    def test_loads(self):
        s = "a = 1\nb = 2\n"
        d = tomlrw.loads(s)
        assert d == {"a": 1, "b": 2}

    def test_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.toml")
            with open(path, "w") as f:
                f.write("a = 1\nb = 2\n")
            
            with open(path, "rb") as f:
                d = tomlrw.load(f)
            assert d == {"a": 1, "b": 2}