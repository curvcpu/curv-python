from rich.console import Console
from typing import Optional
from rich.traceback import install
from rich.logging import RichHandler
import logging

def configure_rich_root_logger(
    verbosity: int = 0, 
    err_console: Optional[Console] = None,
    addl_consoles: Optional[list[Console]] = None
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
    if err_console is None:
        err_console = Console(stderr=True)
    if addl_consoles is None:
        addl_consoles = []
    import click # just so we can suppress click tracebacks
    tracebacks_suppress = [click] # type: ignore

    match verbosity:
        case v if v <= -1:
            level = logging.CRITICAL
            err_console.quiet = True
        # case 0 is handled by the default case
        case 1:
            level = logging.WARNING
        case 2:
            level = logging.INFO
        case v if v >= 3:
            level = logging.DEBUG
        case _:
            level = logging.ERROR
    
    # install rich tracebacks for console.log() and uncaught exceptions
    show_path_map: dict[Console, bool] = {}
    for c in [err_console] + addl_consoles:
        # only show path if there is enough width in the console
        show_path_map[c] = (c.width is not None and c.width >= 80)
        install(
            console=c, 
            show_locals=True, 
            suppress=tracebacks_suppress,
            word_wrap=True)

    # configure logging
    FORMAT = "%(message)s"
    logging.basicConfig(
        force=True,  # in case we're reconfiguring logging
        level=level, 
        format=FORMAT, 
        datefmt="[%X]", 
        handlers=[RichHandler(
            console=err_console,
            show_level=True, 
            show_path=show_path_map[err_console],
            enable_link_path=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            tracebacks_width=120,
            # tracebacks_extra_lines=5,
            tracebacks_code_width=150,
            tracebacks_word_wrap=True,
            tracebacks_suppress=tracebacks_suppress
        )]
    )
