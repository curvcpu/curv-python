"""Unit tests for curvpyutils.shellutils."""

import os
import tempfile
from pathlib import Path

import pytest

from curvpyutils.shellutils import Which, get_console_height, get_console_width

pytestmark = [pytest.mark.unit]


class TestWhich:
    def test_which_finds_python(self):
        which = Which("python3", on_missing_action=Which.OnMissingAction.QUIET)
        result = which()
        assert result is not None
        assert isinstance(result, Path)
        assert result.name in ["python3", "python3.exe"]

    def test_which_returns_none_for_nonexistent_tool(self):
        which = Which("nonexistent_tool_12345", on_missing_action=Which.OnMissingAction.QUIET)
        result = which()
        assert result is None

    def test_which_with_custom_path(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".sh") as temp:
            temp.write("#!/bin/bash\necho 'test'\n")
            temp_path = temp.name

        try:
            os.chmod(temp_path, 0o755)
            which = Which("test_tool", tool_bin_path=temp_path, on_missing_action=Which.OnMissingAction.QUIET)
            result = which()
            assert result is not None
            assert str(result) == temp_path
        finally:
            os.unlink(temp_path)

    def test_which_with_invalid_custom_path(self):
        which = Which(
            "test_tool",
            tool_bin_path="/nonexistent/path/tool",
            on_missing_action=Which.OnMissingAction.QUIET,
        )
        result = which()
        assert result is None

    def test_which_raises_on_missing_when_configured(self):
        which = Which("nonexistent_tool_12345", on_missing_action=Which.OnMissingAction.RAISE)
        with pytest.raises(FileNotFoundError):
            which()

    def test_which_normalizes_tool_name_to_lowercase(self):
        which = Which("PYTHON3", on_missing_action=Which.OnMissingAction.QUIET)
        assert which.tool_name == "python3"

    def test_which_on_missing_action_enum(self):
        assert Which.OnMissingAction.QUIET.value == "quiet"
        assert Which.OnMissingAction.ERROR.value == "error"
        assert Which.OnMissingAction.WARNING.value == "warning"
        assert Which.OnMissingAction.ERROR_AND_RAISE.value == "error_and_raise"


class TestConsole:
    def test_get_console_width(self):
        width = get_console_width()
        assert width > 0
        assert width <= 1_000_000

    def test_get_console_height(self):
        height = get_console_height()
        assert height > 0
        assert height <= 1_000_000

