from __future__ import annotations
import argparse
from rich.console import Console
from rich.text import Text
from rich.markup import escape

class RichHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def __init__(self, prog, indent_increment=2, max_help_position=24, width=None):
        super().__init__(prog, indent_increment, max_help_position, width)
        self._console = Console(force_terminal=True, width=width)
    
    def _format_action(self, action):
        # Get the standard formatting
        parts = super()._format_action(action)
        
        # Convert Rich markup to ANSI
        parts = self._rich_to_ansi(parts)
        return parts
    
    def _rich_to_ansi(self, text: str) -> str:
        """Convert Rich markup to ANSI escape codes"""
        if not text:
            return text
        
        # Use Rich to render markup to ANSI
        with self._console.capture() as capture:
            self._console.print(text, end="")
        return capture.get()
    
    def _format_usage(self, usage, actions, groups, prefix):
        usage_text = super()._format_usage(usage, actions, groups, prefix)
        return self._rich_to_ansi(usage_text)
    
    def _format_text(self, text):
        text = super()._format_text(text)
        return self._rich_to_ansi(text)

    def _format_epilog(self, epilog):
        epilog_text = super()._format_epilog(epilog)
        return self._rich_to_ansi(epilog_text)
    
    def _format_help(self, help):
        help_text = super()._format_help(help)
        return self._rich_to_ansi(help_text)
    
    def _format_heading(self, heading):
        heading_text = super()._format_heading(heading)
        return self._rich_to_ansi(heading_text)