from curvpyutils.colors import AnsiColorsTool
from rich.console import Console
from rich.text import Text
import re
import click
from click.formatting import measure_table, iter_rows, wrap_text
from click._compat import term_len
from click._textwrap import TextWrapper

###############################################################################
#
# Color helpers
#
###############################################################################

ansi = AnsiColorsTool()

# Covers CSI, OSC (including OSC 8 hyperlinks), and single-char escapes
_ANSI_ALL_RE = re.compile(
    r"(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~]"       # CSI sequences
    r"|\x1B\][^\x07\x1b]*(?:\x07|\x1b\\)"     # OSC ... BEL or ST (incl. hyperlinks)
    r"|\x1B[@-Z\\-_]"                         # 7-bit C1 (single char)
)

def _strip_ansi_all(value: str) -> str:
    return _ANSI_ALL_RE.sub("", value)

# Patch Click’s internals so width/length calculations use the stronger stripper
click._compat._ansi_re = _ANSI_ALL_RE
click._compat.strip_ansi = _strip_ansi_all

# Modules import strip_ansi at import time; update their bindings too
import click.termui as _termui
import click.formatting as _fmt
_termui.strip_ansi = _strip_ansi_all
_fmt.strip_ansi = _strip_ansi_all

def colorize_path(path: str) -> str:
    return f"{ansi.br_green}{path}{ansi.reset}"
def colorize_keyword(s: str) -> str:
    return f"{ansi.br_yellow}{s}{ansi.reset}"

# EPILOG = (
#     f"Variable Expansion:\n"
#     f"{colorize_keyword('<curv-root-dir>')} or {colorize_keyword('%CURV_ROOT_DIR%')} => current value of CURV_ROOT_DIR\n"
#     f"{colorize_keyword('<build-dir>')} or {colorize_keyword('%build-dir%')} => current value of --build-dir\n"
# )

import click
from rich.console import Console
from rich.markup import escape
from rich.theme import Theme
from rich.highlighter import Highlighter, RegexHighlighter, ReprHighlighter

theme = Theme({
    "repr.path": "green",   # <- affects pathlib.Path and path-like substrings
    "repr.filename": "bold bright_green",
    # "repr.number": "bold yellow",
}, inherit=False)

# Composite so we can layer multiple highlighters
class CompositeHighlighter(Highlighter):
    def __init__(self, *highlighters):
        self._hls = highlighters
    def highlight(self, text):
        for hl in self._hls:
            hl.highlight(text)

# Path highlighter that supports <var> and %VAR% segments
class CurvcfgPathHighlighter(RegexHighlighter):
    """
    - Highlights generic paths (Unix/Windows), requiring at least one separator.
    - Any segment can be <var> or %VAR%.
    - Highlights [default: …] payload as a path even if it has no separator.
    - Highlights the final component (after the last slash) as repr.filename.
    """
    base_style = "repr."

    _SEG   = r"(?:<[-A-Za-z0-9_]+>|(?i:%[-A-Za-z0-9_]+%)|[^\\/\s:;\]]+)"
    _SEPS  = r"[\\/]"
    _HEAD  = r"(?:[A-Za-z]:[\\/]|~|\.{1,2}|%s)" % _SEG  # start segment (no leading slash required)

    highlights = [
        # 1) Generic path with at least one separator (relative or absolute)
        rf"""(?x)
        (?P<path>
            {_HEAD}
            (?:{_SEPS}{_SEG})+
        )
        """,

        # 2) Final component of any path (used to override with repr.filename)
        rf"""(?x)
        (?P<filename>
            (?<={_SEPS})
            {_SEG}
        )
        """,

        # 3) [default: PAYLOAD] — style the payload as a path even if single-component
        rf"""(?x)
        \[
            (?i:default)      # case-insensitive 'default'
            :
            \s*
            (?P<path> [^\]]+ )
        \]
        """,

        # 4) [default: ...] — style the *last component* of the payload as repr.filename
        rf"""(?x)
        \[
            (?i:default)
            :
            \s*
            (?: .*? {_SEPS} )?      # non-greedy up to last separator if present
            (?P<filename> {_SEG} )
        \]
        """,
    ]

class CurvcfgReprHighlighter(ReprHighlighter):
    """
    Drop-in replacement for the path/filename rule in ReprHighlighter to allow
    - paths without a leading slash
    - segments of the form <var-name> or %VAR_NAME%
    while retaining other default repr highlighting rules.
    """
    # Segment: <var>, %VAR%, or a normal token (no slash)
    _SEG = r"(?:<[-A-Za-z0-9_]+(?:-[-A-Za-z0-9_]+)*>|%[-A-Za-z0-9_]+%|[-A-Za-z0-9._+]+)"
    # Path: optional leading slash, then one or more SEG/ pairs, optional filename at end
    _PATH = rf"(?P<path>(?:/?{_SEG}/)+)(?P<filename>{_SEG})?"

    highlights = []
    for _pat in ReprHighlighter.highlights:
        if "(?P<path>" in _pat and "(?P<filename>" in _pat:
            highlights.append(_PATH)
        else:
            highlights.append(_pat)

###############################################################################
#
# Help formatter class
#
###############################################################################

class CurvcfgAnsiHelpFormatter(click.HelpFormatter):
    """HelpFormatter that accepts Rich markup and converts it to ANSI but lets Click do the alignment and wrapping."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        # No wrapping by Rich; Click will wrap. We only want ANSI.
        self._console = Console(
            force_terminal=True,
            soft_wrap=True,                               # let Click do wrapping
            theme=theme,
            highlighter=CompositeHighlighter(
                CurvcfgReprHighlighter(),
                CurvcfgPathHighlighter(),                 # adds <var>/%%VAR%% support in strings
            ),
            highlight=True,
        )
        self._placeholder_protection_enabled = True

    def _protect_placeholders(self, s: str) -> str:
        """Prevent line breaks inside <...> and %...% placeholders by replacing
        interior hyphens and spaces with non-breaking counterparts.
        """
        if not s:
            return s
        def _nb_inside(match: re.Match) -> str:
            payload = match.group(0)
            open_delim = payload[0]
            close_delim = payload[-1]
            inner = payload[1:-1]
            inner = inner.replace("-", "\u2011")  # non-breaking hyphen
            inner = inner.replace(" ", "\u00A0")  # non-breaking space
            return f"{open_delim}{inner}{close_delim}"

        # Protect <...>
        s = re.sub(r"<[^>\n]+>", _nb_inside, s)
        # Protect %...%
        s = re.sub(r"%[^%\n]+%", _nb_inside, s)
        return s

    from contextlib import contextmanager
    @contextmanager
    def no_placeholder_protection(self):
        prev = self._placeholder_protection_enabled
        self._placeholder_protection_enabled = False
        try:
            yield
        finally:
            self._placeholder_protection_enabled = prev

    def _ansi(self, markup: str) -> str:
        # Render markup to ANSI (no Rich wrapping)
        with self._console.capture() as cap:
            self._console.print(markup, end="")
        return cap.get()

    # Override the low-level writers and feed them ANSI strings
    def write_heading(self, heading: str) -> None:
        super().write_heading(self._ansi(f"[bold]{escape(heading)}[/]"))

    def write_usage(self, prog: str, args: str = "", prefix: str = "Usage: ") -> None:
        super().write_usage(prog, args, prefix=self._ansi(f"[bold]{escape(prefix)}[/]"))

    def write_text(self, text: str) -> None:
        indent = " " * self.current_indent
        if self._placeholder_protection_enabled:
            text = self._protect_placeholders(text)
        wrapped = wrap_text(
            text,
            self.width,
            initial_indent=indent,
            subsequent_indent=indent,
            preserve_paragraphs=True,
        )
        lines = wrapped.splitlines()
        for line in lines:
            self.write(self._ansi(escape(line)))
            self.write("\n")
        self.write("\n")

    def write_dl(self, rows, col_max=30, col_spacing=2) -> None:
        rows = list(rows)
        widths = measure_table(rows)
        if len(widths) != 2:
            raise TypeError("Expected two columns for definition list")

        first_col = min(widths[0], col_max) + col_spacing

        for first, second in iter_rows(rows, len(widths)):
            # Left column (term) printed with current indent; style applied after spacing calc
            self.write(f"{'':>{self.current_indent}}")
            styled_first = self._ansi(f"[cyan]{escape(first)}[/]") if first else first
            self.write(styled_first or "")

            if not second:
                self.write("\n")
                continue

            if term_len(first) <= first_col - col_spacing:
                self.write(" " * (first_col - term_len(first)))
            else:
                self.write("\n")
                self.write(" " * (first_col + self.current_indent))

            text_width = max(self.width - first_col - 2, 10)
            # Optional protection plus wrap without breaking on hyphens
            if self._placeholder_protection_enabled and second:
                second = self._protect_placeholders(second)
            tw = TextWrapper(
                text_width,
                replace_whitespace=False,
            )
            tw.break_long_words = False
            tw.break_on_hyphens = False
            wrapped_text = tw.fill(second)
            lines = wrapped_text.splitlines()

            if lines:
                self.write(f"{self._ansi(escape(lines[0]))}\n")

                for line in lines[1:]:
                    self.write(f"{'':>{first_col + self.current_indent}}{self._ansi(escape(line))}\n")
            else:
                self.write("\n")

    def write_dl_with_markup(self, rows, col_max=30, col_spacing=2) -> None:
        """ Writes a definition list with pre-styled rows (already have markup)"""
        styled = []
        for term, definition in rows:
            t = self._ansi(f"{term}") if term else term
            d = self._ansi(f"{definition}") if definition else definition
            styled.append((t, d))
        super().write_dl(styled, col_max=col_max, col_spacing=col_spacing)

###############################################################################
#
# Context and command classes
#
###############################################################################

class CurvcfgContext(click.Context):
    """ 
    Context that supplies our formatter to Click's help pipeline
    """
    def __init__(self, *args, **kwargs):
        self.color = True
        super().__init__(*args, **kwargs)
    def make_formatter(self) -> click.HelpFormatter:
        return CurvcfgAnsiHelpFormatter(
            width=self.terminal_width, max_width=self.max_content_width
        )

class CurvcfgCommand(click.Command):
    """ Command that uses our context """
    context_class = CurvcfgContext
    def get_help(self, ctx):
        f = CurvcfgAnsiHelpFormatter(width=ctx.terminal_width, max_width=ctx.max_content_width)
        self.format_help(ctx, f)
        return f.getvalue()
    def format_help(self, ctx, formatter):
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_expansion_variables(ctx, formatter)
        self.format_epilog(ctx, formatter)
    def format_expansion_variables(self, ctx, formatter:CurvcfgAnsiHelpFormatter) -> None:
        """Writes all the expansion variables into the formatter if they exist."""
        opts = []
        with formatter.no_placeholder_protection():
            with formatter.section("Expansion Variables"):
                formatter.write_text("These angle-bracket variables will be expanded with the values of other arguments or env vars when used in a quoted path:")
                formatter.write_dl_with_markup([
                    ("[cyan]<curv-root-dir>[/]", "expanded to value of --curv-root-dir or $CURV_ROOT_DIR"),
                    ("[cyan]<build-dir>[/]", "expanded to value of --build-dir"),
                ])
    def format_epilog(self, ctx, formatter:CurvcfgAnsiHelpFormatter) -> None:
        """Writes the epilog into the formatter if it exists."""
        import inspect
        from curvtools.cli.curvcfg.cli import epilog_fn
        global epilog_fn
        self.epilog = epilog_fn()
        if self.epilog:
            epilog = inspect.cleandoc(self.epilog)
            formatter.write_paragraph()
            with formatter.section("CURV_ROOT_DIR"):
                formatter.write_text(epilog)


class CurvcfgGroup(click.Group):
    """ Group that uses our context """
    context_class = CurvcfgContext
    def get_help(self, ctx):
        f = CurvcfgAnsiHelpFormatter(width=ctx.terminal_width, max_width=ctx.max_content_width)
        self.format_help(ctx, f)
        return f.getvalue()
    def format_help(self, ctx, formatter):
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_epilog(ctx, formatter)
    def format_epilog(self, ctx, formatter:CurvcfgAnsiHelpFormatter) -> None:
        """Writes the epilog into the formatter if it exists."""
        import inspect
        from curvtools.cli.curvcfg.cli import epilog_fn
        global epilog_fn
        self.epilog = epilog_fn()
        if self.epilog:
            epilog = inspect.cleandoc(self.epilog)
            formatter.write_paragraph()
            with formatter.section("CURV_ROOT_DIR"):
                formatter.write_text(epilog)

