#!/usr/bin/env -S uv run --all-packages

from __future__ import annotations

# /// package scripts/publish-tools/src/canonical_remote.py
# name = "canonical_remote"
# requires-python = ">=3.10"
# dependencies = ["rich>=13"]
# description = "Find the canonical remote for a given repository"
# entry-points = {
#     "console_scripts": [
#         "canonical-remote = canonical_remote:main",
#     ],
# }
# ///

"""
Uses `git remote -v` to find the canonical remote for the current repository or one
specified by CLI args for hostname (e.g., github.com), organization (e.g., curvcpu), 
and repository (e.g., curv-python).

Example:
    $ canonical-remote
    origin

Example:
    $ canonical-remote github.com curvcpu curv-python
    origin
"""

import re
import subprocess
from typing import Iterable, Dict, List, Tuple, Optional
import argparse
from rich.traceback import install, Traceback
from rich.console import Console
from rich.console import Console
from cli_helpers import RichHelpFormatter
import sys


DEFAULT_HOSTNAME = "github.com"
DEFAULT_ORG = "curvcpu"
DEFAULT_REPO = "curv-python"

console = Console()

def _build_url_pattern(hostname: str, org: str, repo: str) -> re.Pattern:
    """
    Build a regex that matches typical Git URLs pointing at:
        hostname/org/repo(.git)?
    for SSH and HTTP(S) forms.
    """
    host = re.escape(hostname)
    org_esc = re.escape(org)
    repo_esc = re.escape(repo)

    # Matches e.g.:
    #   git@github.com:org/repo.git
    #   ssh://git@github.com/org/repo.git
    #   https://github.com/org/repo.git
    #   http://github.com/org/repo.git
    #   git://github.com/org/repo.git
    pattern = rf"""
        ^
        (?:
            git@{host}[:/]{org_esc}/{repo_esc}(?:\.git)? |
            ssh://git@{host}/{org_esc}/{repo_esc}(?:\.git)? |
            https?://{host}/{org_esc}/{repo_esc}(?:\.git)? |
            git://{host}/{org_esc}/{repo_esc}(?:\.git)?
        )
        $
    """
    return re.compile(pattern, re.VERBOSE)


def find_canonical_remote(
    hostname: str,
    org: str,
    repo: str,
    lines: Optional[Iterable[str]] = None,
) -> str:
    """
    Determine the unique remote name whose fetch AND push URLs all point at
    hostname/org/repo(.git).

    - If no remote matches: raises RuntimeError.
    - If more than one remote name matches: raises RuntimeError.
    - If the matching remote's fetch and push URLs are not both canonical
      (or one side missing): raises RuntimeError.

    If 'lines' is None, runs 'git remote -v' to obtain them.
    """
    pat = _build_url_pattern(hostname, org, repo)

    if lines is None:
        out = subprocess.check_output(["git", "remote", "-v"], text=True)
        lines = out.splitlines()

    # remotes[name] = {
    #   "fetch_urls": [...],
    #   "fetch_matches": [...],
    #   "push_urls": [...],
    #   "push_matches": [...],
    # }
    remotes: Dict[str, Dict[str, List]] = {}

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        # Expect: <name> <url> (fetch|push)
        if len(parts) < 3:
            continue
        name, url, kind_token = parts[0], parts[1], parts[2]

        if kind_token not in ("(fetch)", "(push)"):
            continue

        kind = "fetch" if kind_token == "(fetch)" else "push"
        matches = bool(pat.match(url))

        info = remotes.setdefault(
            name,
            {
                "fetch_urls": [],
                "fetch_matches": [],
                "push_urls": [],
                "push_matches": [],
            },
        )
        info[f"{kind}_urls"].append(url)
        info[f"{kind}_matches"].append(matches)

    # Collect all remote names that use the canonical URL in either direction.
    canonical_names = set()
    for name, info in remotes.items():
        if any(info["fetch_matches"]) or any(info["push_matches"]):
            canonical_names.add(name)

    target = f"{hostname}/{org}/{repo}"

    if not canonical_names:
        raise RuntimeError(f"No remote points at {target}")

    if len(canonical_names) > 1:
        names_str = ", ".join(sorted(canonical_names))
        raise RuntimeError(
            f"Multiple remotes point at {target}: {names_str}"
        )

    remote_name = next(iter(canonical_names))
    info = remotes[remote_name]

    # Require that this remote has BOTH fetch and push URLs configured,
    # and that ALL of those URLs point at the canonical repo.
    if not info["fetch_urls"] or not info["push_urls"]:
        raise RuntimeError(
            f"Remote '{remote_name}' must have both fetch and push URLs"
        )

    if not all(info["fetch_matches"]) or not all(info["push_matches"]):
        # This catches:
        #   - fetch canonical, push different URL
        #   - push canonical, fetch different URL
        #   - multiple URLs for a side where only some are canonical
        raise RuntimeError(
            f"Remote '{remote_name}' has mismatched fetch/push URLs; "
            f"all must point at {target}"
        )

    return remote_name

def parse_args() -> argparse.Namespace:
    """
    Parse the command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="""
Finds the canonical name of the remote on this system for a specific URL. The
purpose of this is to ensure that publishing is done to the correct remote.
""",
        formatter_class=RichHelpFormatter,
        prog="canonical-remote",
        epilog="""
examples:
    $ [bold]%(prog)s github.com curvcpu curv-python[/bold]
    [green3]origin[/green3]
    $ [bold]%(prog)s github.com curvcpu other-repo[/bold]
    [bold red]ERROR:[/bold red] Multiple remotes point at github.com/curvcpu/other-repo: origin, upstream
""",
    )
    parser.add_argument("hostname", metavar="HOSTNAME", nargs="?", default=DEFAULT_HOSTNAME, help="hostname of the repository (default: [bold]%(default)s[/bold])")
    parser.add_argument("org", metavar="ORG", nargs="?", default=DEFAULT_ORG, help="organization of the repository (default: [bold]%(default)s[/bold])")
    parser.add_argument("repo", metavar="REPO", nargs="?", default=DEFAULT_REPO, help="repository of the repository (default: [bold]%(default)s[/bold])")
    args = parser.parse_args()
    return args

def main() -> None:
    install(show_locals=True)
    args = parse_args()
    try:
        remote = find_canonical_remote(args.hostname, args.org, args.repo)
        print(remote)
        return 0
    except Exception as e:
        console.print(f"[bold red]ERROR:[/bold red] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())