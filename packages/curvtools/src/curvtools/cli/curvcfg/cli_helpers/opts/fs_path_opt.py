"""
Base class for any parameter that accepts a filesystem path.
"""

import sys
import os
import click
from pathlib import Path
from curvtools.cli.curvcfg.cli_helpers.opts.expand_special_vars import expand_curv_root_dir_vars, expand_build_dir_vars
from curvtools.cli.curvcfg.cli_helpers.help_formatter.help_formatter import CurvcfgHelpFormatterContext
from click.shell_completion import CompletionItem
from click.types import Path as ClickPath
import re

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
        if not Path(resolved).is_absolute():
            raise click.ClickException(f"Profile TOML file '{resolved}' should be an absolute path")
        return super().__new__(cls, resolved)

    def __str__(self) -> str:
        # this will return an absolute path, even if it does not exist
        return super().__str__()

    def __repr__(self) -> str:
        return f"FsPathType({super().__str__()})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FsPathType):
            return False
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(str(self))

    def mk_rel_to_cwd(self) -> str:
        cwd = Path.cwd()
        try:
            return str(self.relative_to(cwd))
        except ValueError:
            return str(self)

def shell_complete_dir_path(ctx: click.Context, param: click.Parameter, incomplete: str) -> list[CompletionItem]:
    items: list[CompletionItem] = []
    items.append(CompletionItem(None, type="dir", help='path build base config toml'))
    return items

def shell_complete_file_path(ctx: click.Context, param: click.Parameter, incomplete: str) -> list[CompletionItem]:
    items: list[CompletionItem] = []
    items.append(CompletionItem(None, type="file", help='path build base config toml'))
    return items

def make_fs_path_param_type_class(dir_okay: bool = False, file_okay: bool = False, exists: bool = False, default_value_if_omitted: str = None, raw_string_handling: dict[str, str] = None) -> type[click.ParamType]:
    class FsPathParamType(ClickPath):
        """
        Base class for any parameter that accepts a filesystem path, including special variables like <curv-root-dir>
        and <build-dir> that can be expanded to generate the absolute path.
        """
        # appears in help text as "Filesystem path that expands special variables like <curv-root-dir> and <build-dir> to generate an absolute path."
        name = (
            "Filesystem path that expands special variables like <curv-root-dir> and <build-dir> to generate an "
            "absolute path."
        )

        def __init__(self, *args, **kwargs):
            kwargs['path_type'] = FsPathType
            kwargs['dir_okay'] = dir_okay
            kwargs['file_okay'] = file_okay
            if exists:
                kwargs['exists'] = True
                kwargs['resolve_path'] = True
            else:
                kwargs['exists'] = False
                kwargs['resolve_path'] = False
            super().__init__(*args, **kwargs)

            # handling for raw strings is done with `raw_string_handling`, a dict with keys 'prefix' and 'suffix'
            # that we'll try to add to a simple name to turn it into a file path
            if raw_string_handling is not None:
                raw_string_prefix = raw_string_handling.get("prefix", "")
                raw_string_suffix = raw_string_handling.get("suffix", "")
                self.raw_string_convert_func = lambda x: f"{raw_string_prefix}{x}{raw_string_suffix}"
            else:
                self.raw_string_convert_func = lambda x: x
        
        def _is_raw_string(self, value: str) -> bool:
            ext_pat = re.compile(r'\.[a-zA-Z0-9_-]+$')
            return (
                not "/" in value and 
                not "$(" in value and 
                not "${" in value and 
                (ext_pat.search(value) is None)
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
                s = str(value)
                if self.raw_string_convert_func is not None and self._is_raw_string(s):
                    s = self.raw_string_convert_func(s)
                s = expand_curv_root_dir_vars(s, ctx)
                s = expand_build_dir_vars(s, ctx)
                obj = super().convert(s, param, ctx)
                return obj
            except Exception as e:
                if not self.exists and default_value_if_omitted is not None and not str(value):
                    s = default_value_if_omitted
                    if self.raw_string_convert_func is not None and self._is_raw_string(s):
                        s = self.raw_string_convert_func(s)
                    s = expand_curv_root_dir_vars(s, ctx)
                    s = expand_build_dir_vars(s, ctx)
                    return super().convert(s, param, ctx)
                self.fail(f"Unable to parse filesystem path {value!r}: {e}")
        
        def shell_complete(self, ctx: click.Context, param: click.Parameter, incomplete: str) -> list[CompletionItem]:
            #print(f"😀😀😀 shell_complete: {incomplete}", file=sys.stderr)
            if dir_okay:
                return shell_complete_dir_path(ctx, param, incomplete)
            if file_okay:
                return shell_complete_file_path(ctx, param, incomplete)

    return FsPathParamType()

