"""Tests for curvpyutils.shellutils.delta fallbacks when `delta` is missing."""

from pathlib import Path

import pytest


pytestmark = [pytest.mark.unit]


def test_print_delta_falls_back_to_difflib_when_missing_delta_and_diff(tmp_path, monkeypatch, capsys):
    # Arrange: create two different files
    file1: Path = tmp_path / "file1.txt"
    file2: Path = tmp_path / "file2.txt"
    file1.write_text("""line1\ncommon\nold\nend\n""")
    file2.write_text("""line1\ncommon\nnew\nend\n""")

    # Monkeypatch shutil.which used inside curvpyutils.shellutils.which to hide delta and diff
    import curvpyutils.shellutils.which as which_mod

    real_shutil_which = which_mod.shutil.which

    def fake_which(name, *args, **kwargs):
        if name in ("delta", "diff"):
            return None
        return real_shutil_which(name, *args, **kwargs)

    monkeypatch.setattr(which_mod.shutil, "which", fake_which)

    # Act: call print_delta; should not raise and should fall back to difflib unified diff
    from curvpyutils.shellutils import print_delta, Which

    print_delta(file1, file2, on_delta_missing=Which.OnMissingAction.ERROR_AND_RAISE)

    captured = capsys.readouterr()
    out = captured.out

    # Assert: difflib unified diff markers are present
    assert "--- " in out
    assert "+++ " in out
    assert "@@" in out


