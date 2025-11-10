"""
Base class for any parameter that accepts a filesystem path.
"""

import sys
import os
import click
from pathlib import Path
from curvtools.cli.curvcfg.cli_helpers.opts.expand_special_vars import expand_curv_root_dir_vars, expand_build_dir_vars
from curvtools.cli.curvcfg.cli_helpers.help_formatter.help_formatter import CurvcfgContext
from click.shell_completion import CompletionItem

_SystemPath = type(Path())

class FsPathType(_SystemPath):
    """
    A filesystem path that expands special variables like <curv-root-dir> and <build-dir> to generate an 
    absolute path. The path is resolved against the current working directory unless it is an absolute path
    (begins with a separator) in which case we only do variable expansion.
    """
    _flavour = _SystemPath._flavour
    def __new__(cls, path: str):
        resolved = str(Path(path).expanduser().absolute())
        return super().__new__(cls, resolved)

    def __str__(self) -> str:
        return super().__str__()

    def __repr__(self) -> str:
        return f"FsPathType({super().__str__()})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FsPathType):
            return False
        return super().__eq__(other)

def shell_complete_dir_path(ctx: click.Context, param: click.Parameter, incomplete: str) -> list[CompletionItem]:
    items: list[CompletionItem] = []
    items.append(CompletionItem(None, type="dir", help='path build base config toml'))
    return items

def shell_complete_file_path(ctx: click.Context, param: click.Parameter, incomplete: str) -> list[CompletionItem]:
    items: list[CompletionItem] = []
    items.append(CompletionItem(None, type="file", help='path build base config toml'))
    return items

def make_fs_path_param_type_class(must_be_dir: bool = False, must_be_file: bool = False, default_value: str = None) -> type[click.ParamType]:
    class FsPathParamType(click.ParamType):
        """
        Base class for any parameter that accepts a filesystem path, including special variables like <curv-root-dir>
        and <build-dir> that can be expanded to generate the absolute path.
        """
        # appears in help text as "Filesystem path that expands special variables like <curv-root-dir> and <build-dir> to generate an absolute path."
        name = (
            "Filesystem path that expands special variables like <curv-root-dir> and <build-dir> to generate an "
            "absolute path."
        )

        def convert(self, value: str|None, param: click.Parameter, ctx: click.Context) -> "FsPathType":
            # None must return None
            if value is None:
                return None
            # allow passing an already-constructed object (useful in tests/callbacks)
            if isinstance(value, FsPathType):
                return value
            if not isinstance(value, (str, os.PathLike)):
                self.fail(f"Expected a path-like value, got {type(value).__name__}")
            try:
                s = expand_curv_root_dir_vars(str(value), ctx)
                s = expand_build_dir_vars(s, ctx)
                return FsPathType(s)
            except Exception as e:
                if default_value is not None:
                    s = expand_curv_root_dir_vars(str(default_value), ctx)
                    s = expand_build_dir_vars(s, ctx)
                    return FsPathType(s)
                self.fail(f"Unable to parse filesystem path {value!r} ({e})")
        
        def shell_complete(self, ctx: click.Context, param: click.Parameter, incomplete: str) -> list[CompletionItem]:
            print(f"😀😀😀 shell_complete: {incomplete}", file=sys.stderr)
            if must_be_dir:
                return shell_complete_dir_path(ctx, param, incomplete)
            if must_be_file:
                return shell_complete_file_path(ctx, param, incomplete)

    return FsPathParamType()

