"""Unit tests for curvpyutils.str_utils.insert_underscores."""

import pytest
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from curvpyutils.str_utils import insert_underscores

pytestmark = [pytest.mark.unit]

class TestInsertUnderscores:
    def test_insert_underscores(self) -> None:
        console = Console()
        try:
            assert insert_underscores("0x12345678") == "0x1234_5678"
            assert insert_underscores("0x12345678", start_left=True) == "0x1234_5678"
            assert insert_underscores("0b1010") == "0b1010"
            assert insert_underscores("0b1010", start_left=True) == "0b1010"
            assert insert_underscores("32'h12345678") == "32'h1234_5678"
            assert insert_underscores("32'h123456789A") == "32'h12_3456_789A"
            assert insert_underscores("32'h123456789A", start_left=True) == "32'h1234_5678_9A"
            assert insert_underscores("12345678") == "1234_5678"
            assert insert_underscores("12345678", start_left=True) == "1234_5678"
            assert insert_underscores("12345678", N=2) == "12_34_56_78"
            assert insert_underscores("12345678", start_left=True, N=2) == "12_34_56_78"

            # already has underscores, should remove them first
            assert insert_underscores("12_34_56_78") == "1234_5678"
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

