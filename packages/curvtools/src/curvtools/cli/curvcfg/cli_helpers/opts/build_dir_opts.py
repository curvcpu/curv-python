import click
import os
from pathlib import Path
from click.shell_completion import CompletionItem
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import make_fs_path_param_type_class, FsPathType

###############################################################################
#
# Common flags: build dir
#
###############################################################################

def _iter_matching_dirs(incomplete: str | None) -> list[str]:
    prefix = os.path.expanduser(incomplete or "")
    path = Path(prefix)

    if prefix.endswith(os.sep):
        search_dir = path
        match = ""
    else:
        search_dir = path.parent if prefix else Path(".")
        match = path.name if prefix else ""

    try:
        entries = list(search_dir.expanduser().iterdir())
    except OSError:
        return []

    candidates: list[str] = []
    for entry in entries:
        if entry.is_dir() and entry.name.startswith(match):
            candidates.append(str(entry.resolve()) + os.sep)
    candidates.sort()
    return candidates


def shell_complete_build_dir(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> list[CompletionItem]:
    del ctx, param  # currently unused
    matches = _iter_matching_dirs(incomplete)
    if matches:
        return [CompletionItem(value, type="dir", help=value) for value in matches]
    return [CompletionItem(None, type="dir", help="CURV_BUILD_DIR")]

