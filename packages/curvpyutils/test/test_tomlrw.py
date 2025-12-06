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