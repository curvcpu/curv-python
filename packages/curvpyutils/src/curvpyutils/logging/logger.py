from rich.console import Console
from typing import ClassVar, Optional
from rich.traceback import install
from rich.logging import RichHandler
import logging
import os
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

# default width used in log file (if applicable)
DEFAULT_LOG_FILE_WIDTH = 120

@dataclass
class LoggingLevels:
    SILENT: ClassVar[int] = logging.CRITICAL+10
    logging.addLevelName(SILENT, "SILENT") # type: ignore

    stderr_level: int = field(default=logging.ERROR)
    file_level: int = field(default=logging.NOTSET)
    _stderr_level_str: str = field(default="")
    _file_level_str: str = field(default="")
    def __post_init__(self):
        self._stderr_level_str = logging.getLevelName(self.stderr_level)
        self._file_level_str = logging.getLevelName(self.file_level)
    @classmethod
    def from_verbosity(cls, verbosity: int) -> "LoggingLevels":
        match verbosity:
            case v if v <= -1:
                stderr_level = logging.CRITICAL
            # case 0 is handled by the default case
            case 1:
                stderr_level = logging.WARNING
            case 2:
                stderr_level = logging.INFO
            case v if v >= 3:
                stderr_level = logging.DEBUG
            case _:
                stderr_level = logging.ERROR
        return cls(stderr_level=stderr_level, file_level=logging.NOTSET)
    @property
    def stderr_level_str(self) -> str:
        return self._stderr_level_str
    @property
    def file_level_str(self) -> str:
        return self._file_level_str
    @property
    def stderr_quiet(self) -> bool:
        return self.stderr_level >= self.SILENT
    def __str__(self) -> str:
        return f"LoggingLevels(stderr_level={self.stderr_level_str}, file_level={self.file_level_str})"

def configure_rich_root_logger(
    verbosity: int|LoggingLevels = LoggingLevels(), 
    err_console: Optional[Console] = None,
    addl_consoles: Optional[list[Console]] = None,
    log_file_path: Optional[str] = None,
    log_file_width: int = DEFAULT_LOG_FILE_WIDTH,
) -> None:
    """
    Configure the root logger based on the verbosity argument.
    Enables rich tracebacks for the error console and any additional consoles passed in.

    Usage:
        At the top of each module:
        ```python
        import logging
        from curvpyutils.logging import configure_rich_root_logger
        
        log = logging.getLogger(__name__)
        ```

        At the top of main():
        ```python
        def main():
            # assume this sets args.verbosity (-1 to 3)
            args = parse_args()

            configure_rich_root_logger(verbosity=args.verbosity)
        ```
    
    Args:
        verbosity: the verbosity level
            -1: print nothing at all
            0: print only ERROR/CRITICAL/EXCEPTION
            1: print WARNING also
            2: print INFO also
            3: print DEBUG also
        err_console: the console to use for error messages; generally, this should be omitted and
            one will be created on stderr
        addl_consoles: any additional consoles on which to install rich tracebacks

    Returns:
        None
    """
    if isinstance(verbosity, int):
        verbosity = LoggingLevels.from_verbosity(verbosity)
    elif isinstance(verbosity, LoggingLevels):
        pass
    else:
        raise ValueError(f"Invalid verbosity: {verbosity}")

    if err_console is None:
        err_console = Console(stderr=True)
    if verbosity.stderr_quiet:
        err_console.quiet = True
    if log_file_path is not None:
        file_console = Console(file=open(log_file_path, "a", encoding="utf-8"), width=log_file_width)
    else:
        file_console = None
    if addl_consoles is None:
        addl_consoles = []
    import click # just so we can suppress click tracebacks
    tracebacks_suppress = [click] # type: ignore

    # install rich tracebacks for console.log() and uncaught exceptions
    show_path_map: dict[Console, bool] = {}
    for c in [err_console] + addl_consoles + ([file_console] if file_console is not None else []):
        # only show path if there is enough width in the console
        show_path_map[c] = (c.width is not None and c.width >= 80) or (log_file_path is not None and c==file_console)
        install(
            console=c, 
            show_locals=True, 
            suppress=tracebacks_suppress,
            word_wrap=True)

    # configure logging
    FORMAT = "%(message)s"
    handlers=[
        RichHandler(
            console=err_console,
            level=verbosity.stderr_level,
            show_level=True, 
            show_path=show_path_map[err_console],
            enable_link_path=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            tracebacks_width=120,
            # tracebacks_extra_lines=5,
            tracebacks_code_width=150,
            tracebacks_word_wrap=True,
            tracebacks_suppress=tracebacks_suppress,
            omit_repeated_times=False,
        ),
    ]
    if log_file_path is not None:
        handlers.append(
            RichHandler(
                level=verbosity.file_level,
                console=file_console,
                show_level=True, 
                show_path=show_path_map[file_console],
                enable_link_path=True,
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                tracebacks_width=120,
                # tracebacks_extra_lines=5,
                tracebacks_code_width=150,
                tracebacks_word_wrap=True,
                tracebacks_suppress=tracebacks_suppress,
                omit_repeated_times=False,
            )
        )
        # log_file_path2 = log_file_path.replace(
        #     strip_extension(log_file_path), 
        #     strip_extension(log_file_path)+'2'
        # )
        # handlers.append(
        #     # Plain file output
        #     logging.FileHandler(log_file_path2, mode="a", encoding="utf-8"),
        # )
    logging.basicConfig(
        force=True,  # in case we're reconfiguring logging
        level=logging.NOTSET, 
        format=FORMAT, 
        datefmt="[%X]", 
        handlers=handlers
    )
    log.info('-' * min(log_file_width, 80))
    log.info(f"[logger] configured: {str(verbosity)}")
