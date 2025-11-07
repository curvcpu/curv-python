from enum import Enum
import os
from pathlib import Path
from typing import Optional
import shutil

from ..colors import AnsiColorsTool


class Which:
    """Locate a tool in ``PATH`` or at a specific location and report status."""

    class OnMissingAction(Enum):
        QUIET = "quiet"
        ERROR = "error"
        WARNING = "warning"
        RAISE = "raise"
        ERROR_AND_RAISE = "error_and_raise"
        WARNING_AND_RAISE = "warning_and_raise"

    def __init__(
        self,
        tool_name: str,
        tool_bin_path: Optional[str] = None,
        on_missing_action: "Which.OnMissingAction" = OnMissingAction.ERROR_AND_RAISE,
    ):
        self.tool_name = tool_name.lower()
        self.tool_bin_path = tool_bin_path
        self.on_missing_action = on_missing_action

    def __call__(self) -> Optional[Path]:
        if self.tool_bin_path:
            if not os.path.exists(self.tool_bin_path) or not os.access(self.tool_bin_path, os.X_OK):
                return self._handle_missing(self.tool_bin_path)
            return Path(self.tool_bin_path)

        resolved = shutil.which(self.tool_name)
        if resolved is None:
            return self._handle_missing(self.tool_name)
        return Path(resolved)

    def _handle_missing(self, target: str) -> Optional[Path]:
        if self.on_missing_action in (self.OnMissingAction.ERROR, self.OnMissingAction.ERROR_AND_RAISE):
            self._print_error(f"error: {target} not found or not executable\n")
            self._print_install_instructions(self.tool_name)
            if self.on_missing_action == self.OnMissingAction.ERROR_AND_RAISE:
                raise FileNotFoundError(f"{target} not found or not executable")
        elif self.on_missing_action == self.OnMissingAction.WARNING:
            self._print_warning(f"warning: {target} not found or not executable\n")
            self._print_install_instructions(self.tool_name)
        elif self.on_missing_action == self.OnMissingAction.RAISE:
            raise FileNotFoundError(f"{target} not found or not executable")
        elif self.on_missing_action == self.OnMissingAction.WARNING_AND_RAISE:
            self._print_warning(f"warning: {target} not found or not executable\n")
            self._print_install_instructions(self.tool_name)
            raise FileNotFoundError(f"{target} not found or not executable")
        return None

    def _print_error(self, message: str) -> None:
        ansi = AnsiColorsTool()
        print(ansi.bright_red(message), end="")

    def _print_warning(self, message: str) -> None:
        ansi = AnsiColorsTool()
        print(ansi.bright_yellow(message), end="")

    def _print_install_instructions(self, tool_name: str) -> None:
        ansi = AnsiColorsTool()
        if tool_name == "delta":
            print(f"Please install {ansi.bold}delta{ansi.reset}:")
            print("  (macOS) brew install git-delta")
            print("  (Ubuntu/Debian) sudo apt install delta")
        elif tool_name == "slang":
            print(f"Please install {ansi.bold}slang{ansi.reset}")
            print(
                "Instructions to compile and install slang are available in "
                f"{ansi.bright_blue}https://github.com/MikePopoloski/slang.git{ansi.reset} "
                "repo's README.md.\n"
            )
            print("Roughly, it will be something like this:\n")
            print(f"  {ansi.bold}git clone https://github.com/MikePopoloski/slang.git")
            print("  cd slang")
            print("  cmake -B build")
            print(f"  cmake --build build -j{ansi.reset}")
        else:
            print(f"Please install {ansi.bold}{tool_name}{ansi.reset}.")

