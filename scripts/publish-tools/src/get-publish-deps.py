#!/usr/bin/env -S uv run --all-packages

import os, subprocess, sys
from rich.console import Console
from rich.text import Text
import re
from curvpyutils.colors import AnsiColorsTool
from curvpyutils.file_utils import get_git_repo_root
from pathlib import Path
from typing import Iterator
import argparse
from rich.table import Table
from rich.traceback import install, Traceback
from datetime import datetime
from rich.panel import Panel

ansi = AnsiColorsTool()

epilog = \
f"""

This tool answers the question of which packages need to be 
republished in order for another package to be published.
It uses the git commit and tag timestamps to show what's
out of date.

We have roughtly the following dependency tree:

                 +------------------------------+         
                 |                              |         
                 |          curvtools           |         
                 |                              |         
                 +---------/-----------\--------+         
                          /             \                
                         /               \               
                        /                 \             
                       /                   |           
            +---------▼--------+           |           
            |                  |           |           
            |       curv       |           |           
            |                  |           |           
            +---------+--------+           |           
                      |                    |           
                      |                    |           
            +---------▼--------------------▼------+
            |                                     |
            |             curvpyutils             |
            |                                     |
            +-------------------------------------+

In case your editor doesn't use 4-space tabs, here's a better
representation:
  • curvtools → curv → curvpyutils
  • curv → curvpyutils

Run the tool with the name of the package you want to publish,
and it will write to stdout a list of what needs to be published
that make can easily consume:

    ${ansi.dark_blue}# publishing curvtools requires publishing all 3 in this order${ansi.reset}
    $ ${ansi.yellow}get-publish-deps.py curvtools{ansi.reset}
    curvpyutils curv curvtools

    ${ansi.dark_blue}# curv can be published on its own${ansi.reset}
    $ ${ansi.yellow}get-publish-deps.py curv{ansi.reset}
    curv

You can also pass a `-v` flag to see exactly how it is 
reaching its conclusions.

"""

SCRIPT_DIR = Path(get_git_repo_root(cwd=Path(__file__).parent)) / "scripts"
CANONICAL_REMOTE_SCRIPT = SCRIPT_DIR / "publish-tools" / "src" / "canonical_remote.py"

HOSTNAME = "github.com"
ORG = "curvcpu"
REPO = "curv-python"
PUBLISH_BRANCH = "main"

console = Console()
err_console = Console(stderr=True)

# Latest tag timestamp that begins with `curv-v`:
#   git for-each-ref --sort=-creatordate --format='%(refname:short)' 'refs/tags/curv-v*' | head -n 1 | xargs -I{} git for-each-ref --format='%(taggerdate:unix)' refs/tags/{}
#

def get_canonical_remote() -> str | None:
    """
    Returns the local name of whatever remote is pointing at github.com/curvcpu/curv-python
    Sometimes this origin, sometimes upstream, sometimes absent entirely.
    """
    try:
        result = subprocess.run(
            [CANONICAL_REMOTE_SCRIPT, "github.com", "curvcpu", "curv-python"],
            text=True,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        err_console.print(f"[bold red]error:[/bold red] {e}")
        err_console.print(f"[bold red]hint:[/bold red] run `canonical-remote` to see what remote it thinks is pointing at github.com/curvcpu/curv-python")
        sys.exit(1)
    return result.stdout.strip() if result.stdout else None

class PackageInfo:
    def __init__(self, pkg:str):
        self.pkg = pkg
        self.canonical_remote = get_canonical_remote()
        self.latest_commit_ts = self._get_latest_commit_ts()
        self.latest_tag_ts, self.latest_tag_name = self._get_latest_tag_ts_and_name()
    
    def get_latest_commit_ts(self) -> str:
        dt = datetime.fromtimestamp(self.latest_commit_ts)
        time_str = dt.strftime("%I:%M:%S%p").lower()
        tz_str = dt.strftime("%Z")
        return f"{dt.strftime('%Y-%m-%d')} {time_str} {tz_str}"

    def get_latest_tag_ts(self) -> str:
        dt = datetime.fromtimestamp(self.latest_tag_ts)
        time_str = dt.strftime("%I:%M:%S%p").lower()
        tz_str = dt.strftime("%Z")
        return f"{dt.strftime('%Y-%m-%d')} {time_str} {tz_str}"

    def needs_publish(self) -> bool:
        return self.latest_commit_ts > self.latest_tag_ts
        
    def _get_latest_commit_ts(self) -> int|None:
        """
        Get the epoch timestamp of the latest commit that modified any file under `packages/$(PKG)/`:
            git log -1 --format=%ct origin/main -- packages/$(PKG)
        """
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ct", f"{self.canonical_remote}/{PUBLISH_BRANCH}", "--", f"packages/{self.pkg}"],
                text=True,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            err_console.print(f"[bold red]error:[/bold red] couldn't determine the latest commit that chnaged files under `packages/{self.pkg}/`")
            err_console.print(f"[bold red]hint:[/bold red] {e}")
            sys.exit(1)
        return int(result.stdout.strip()) if result.stdout else None

    def _get_latest_tag_ts_and_name(self) -> tuple[str, int]|None:
        """
        Get the epoch timestamp of the latest tag that begins with `$(PKG)-v*`. Equivalent to:
            git for-each-ref --sort=-creatordate --format='%(refname:short)' refs/tags/$(PKG)-v* | \
                head -n1 | xargs -I{} git for-each-ref --format='%(taggerdate:unix)' refs/tags/{}
        """
        try:
            # get all annotated tags that begin with $(PKG)-v*
            # sort them by creation date and take the first one
            result = subprocess.run(
                ["git", "for-each-ref", "--sort=-creatordate", "--format=%(refname:short)", f"refs/tags/{self.pkg}-v*"],
                text=True,
                check=True,
                capture_output=True,
            )
            stdout = result.stdout.strip() if result.stdout else None
            if not stdout:
                return None, None
            
            def sort_by_semver(tag_names: list[str]) -> Iterator[str]:
                """
                Function to sort a list like this:
                    curv-v0.1.14
                    curv-v0.1.13
                    curv-v0.1.12
                    curv-v0.1.11
                    curv-v0.1.10
                    curv-v0.1.9
                in semver order, newest first.
                """
                import sys
                from packaging.version import Version
                tags = [l.strip() for l in tag_names if l.strip()]
                for t in sorted(tags, key=lambda s: Version(s.removeprefix(f"{self.pkg}-v")), reverse=True):
                    yield t
            # console.print(f"sorting tags by semver: [yellow]{stdout}[/yellow]")
            latest_tag_name = next(sort_by_semver(stdout.splitlines()))

            # get the epoch timestamp of the latest tag
            result = subprocess.run(
                ["git", "for-each-ref", "--format=%(taggerdate:unix)", f"refs/tags/{latest_tag_name}"],
                text=True,
                check=True,
                capture_output=True,
            )
            latest_tag_ts = result.stdout.strip() if result.stdout else None
            if not latest_tag_ts:
                return None, None
            return int(latest_tag_ts), latest_tag_name
        except subprocess.CalledProcessError as e:
            err_console.print(f"[bold red]error:[/bold red] couldn't determine the latest tag that begins with `{self.pkg}-v*` or its timestamp ({self.pkg}-v* -> timestamp)")
            err_console.print(f"[bold red]hint:[/bold red] {e}")
            sys.exit(1)
    
def parse_args(argv: list[str]) -> tuple[str, bool]:
    parser = argparse.ArgumentParser(epilog=epilog)
    parser.add_argument("pkg", metavar="PKG", nargs=1, choices=["curv", "curvtools", "curvpyutils"], help="the package you want to publish (choices: curv, curvtools, curvpyutils)")
    parser.add_argument("-v", "--verbose", action="store_true", help="show verbose output on stderr")
    return parser.parse_args(argv)

def main(argv):
    args = parse_args(argv)
    pkg = args.pkg[0]
    verbose = args.verbose

    package_info = PackageInfo(pkg)
    dependencies: list[PackageInfo] = []
    if pkg == "curvpyutils":
        # no dependencies
        pass
    elif pkg == "curv":
        dependencies.append(PackageInfo("curvpyutils"))
    elif pkg == "curvtools":
        # append in order we would publish them if needed
        dependencies.append(PackageInfo("curvpyutils"))
        dependencies.append(PackageInfo("curv"))

    # publish order will be populated with all packages needing to be republished in bottom up order
    publish_order: list[str] = []
    for dep in dependencies:
        if dep.needs_publish():
            publish_order.append(dep.pkg)
    publish_order.append(pkg)
    publish_order_str = " ".join(publish_order)
    
    # print our findings to stdout unless verbose is enabled, then print an entire table
    if not verbose:
        console.print(f"{publish_order_str}")
    else:
        yes_text = Text.from_markup(":p_button: (yes)")
        no_text = Text.from_markup("(no)")

        table = Table(title=f"If you want to publish [bold magenta3]{pkg}[/bold magenta3]...")
        table.add_column("Package")
        table.add_column("Latest Commit Time")
        table.add_column("Latest Tag Time")
        table.add_column("Needs Publish?")
        for p in publish_order:
            table.add_row(p, 
                PackageInfo(p).get_latest_commit_ts(), 
                PackageInfo(p).get_latest_tag_ts(), 
                yes_text if PackageInfo(p).needs_publish() else no_text)
        console.print(f"")
        console.print(table, emoji=True)
        console.print("")
        panel = Panel.fit(
            Text.assemble(
                Text(f"make publish PKG={pkg} LEVEL=patch|minor|major", style="bold white"),
                "\n\n",
                Text(f"(This is because make re-runs this tool to determine all packages needing to be republished in order to publish {pkg}.)", style="dim white"),
            ),
            title=f"Recommended make command for publishing `{pkg}`",
            padding=(1, 2),
            border_style="cyan",
            style="cyan italic",
            highlight=True,
        )
        console.print(panel)

    sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1:])