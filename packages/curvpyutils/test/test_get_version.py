"""Unit tests for curvpyutils.version functions"""

import pytest
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from curvpyutils import get_curvpyutils_version_str, get_curvpyutils_version_tuple

pytestmark = [pytest.mark.unit]

class TestVersion:
    def test_get_curvpyutils_version(self) -> None:
        console = Console()
        try:
            ver_str = get_curvpyutils_version_str()
            ver_tuple = get_curvpyutils_version_tuple()
            assert isinstance(ver_str, str)
            assert isinstance(ver_tuple, tuple)
            assert len(ver_tuple) == 3
        except AssertionError as e:
            # Create a nicely formatted error message with rich
            error_text = Text()
            error_text.append("Test failed!\n\n", style="bold red")
            error_text.append(f"File: {e.__traceback__.tb_frame.f_code.co_filename}, line {e.__traceback__.tb_lineno}\n", style="cyan")
            error_text.append(f"Function: {e.__traceback__.tb_frame.f_code.co_name}\n\n", style="cyan")

            panel = Panel(error_text, title="[bold red]Assertion Error[/bold red]", border_style="red")
            console.print(panel)
            raise e

        # print success message
        success_text = Text("All tests passed!", style="bold green")
        panel = Panel(success_text, title="[bold green]Success[/bold green]", border_style="green")
        console.print(panel)

