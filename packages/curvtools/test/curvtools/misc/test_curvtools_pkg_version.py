from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from curvtools import get_curvtools_version_str

import pytest
pytestmark = [pytest.mark.unit]

class TestCurvtoolsVersion:
    def test_get_version_str(self) -> None:
        console = Console()
        try:
            ver_short = get_curvtools_version_str(short_version=True)
            ver_full = get_curvtools_version_str(short_version=False)
            assert isinstance(ver_short, str)
            assert isinstance(ver_full, str)
            assert ver_short.split('.')[:3] == ver_full.split('.')[:3]
        except AssertionError as e:
            # Create a nicely formatted error message with rich
            error_text = Text()
            error_text.append("TestCurvtoolsVersion failed!\n\n", style="bold red")
            error_text.append(f"File: {e.__traceback__.tb_frame.f_code.co_filename}, line {e.__traceback__.tb_lineno}\n", style="cyan")
            error_text.append(f"Function: {e.__traceback__.tb_frame.f_code.co_name}\n\n", style="cyan")

            panel = Panel(error_text, title="[bold red]Assertion Error[/bold red]", border_style="red")
            console.print(panel)
            raise e

        # print success message
        success_text = Text("TestCurvtoolsVersion passed!", style="bold green")
        panel = Panel(success_text, title="[bold green]Success[/bold green]", border_style="green")
        console.print(panel)

