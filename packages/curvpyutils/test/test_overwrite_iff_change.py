import os
import time
import tempfile
from pathlib import Path

import pytest
from curvpyutils.file_utils import open_write_iff_change

pytestmark = [pytest.mark.unit]

def test_open_write_iff_change_overwrite_when_different():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "test.txt"

        # initial contents
        p.write_text("Hello, world!", encoding="utf-8")
        time.sleep(1)  # ensure mtime separation
        before_mtime = p.stat().st_mtime

        cm = open_write_iff_change(p, "w")

        with cm as f:
            f.write("Something totally different")

        after_mtime = p.stat().st_mtime

        assert p.read_text() == "Something totally different"
        assert after_mtime > before_mtime
        assert cm.changed is True


def test_open_write_iff_change_no_overwrite_when_identical():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "test.txt"

        # initial contents
        p.write_text("Hello, world!", encoding="utf-8")
        time.sleep(1)  # ensure mtime separation
        before_mtime = p.stat().st_mtime

        cm = open_write_iff_change(p, "w")

        with cm as f:
            f.write("Hello, world!")

        after_mtime = p.stat().st_mtime

        assert p.read_text() == "Hello, world!"
        assert after_mtime == before_mtime  # unchanged
        assert cm.changed is False