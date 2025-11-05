#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Tuple, Union
from rich.console import Console
from rich.table import Table
from rich.text import Text
import subprocess

SEMVER_RE = re.compile(
    r"""
    ^
    (?P<major>0|[1-9]\d*)\.
    (?P<minor>0|[1-9]\d*)\.
    (?P<patch>0|[1-9]\d*)
    (?:-(?P<prerelease>(?:[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)))?
    (?:\+(?P<build>(?:[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)))?
    $
    """,
    re.VERBOSE,
)

@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: Optional[List[str]]  # identifiers (split on '.')
    build: Optional[str]             # ignored in ordering

    @staticmethod
    def parse(s: str) -> "SemVer":
        m = SEMVER_RE.match(s)
        if not m:
            raise ValueError(f"not semver: {s}")
        major = int(m.group("major"))
        minor = int(m.group("minor"))
        patch = int(m.group("patch"))
        pr = m.group("prerelease")
        build = m.group("build")
        return SemVer(major, minor, patch, pr.split(".") if pr else None, build)

    def _precedence_key(self) -> Tuple:
        """
        SemVer precedence:
          (major, minor, patch, release_marker, prerelease_key)
        where release_marker = 1 for final releases (so finals > prerelease),
        and prerelease_key compares identifiers per spec:
          - numeric ids compare numerically and are LOWER than non-numeric
          - lexicographic for non-numeric
          - if equal prefix, longer list is HIGHER precedence
        """
        if self.prerelease is None:
            # Finals sort after any prerelease of same M.m.p
            return (self.major, self.minor, self.patch, 1)
        ids = []
        for ident in self.prerelease:
            if ident.isdigit():
                ids.append((0, int(ident)))   # numeric < non-numeric
            else:
                ids.append((1, ident))
        # include length so longer prerelease list > shorter when prefix equal
        return (self.major, self.minor, self.patch, 0, tuple(ids), len(self.prerelease))

    def __lt__(self, other: "SemVer") -> bool:  # type: ignore[override]
        return self._precedence_key() < other._precedence_key()
    
    def get_full_str(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}{f'-{self.prerelease}' if self.prerelease else ''}{f'+{self.build}' if self.build else ''}"

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

def fetch_pypi_json(pkg: str) -> dict:
    url = f"https://pypi.org/pypi/{pkg}/json"
    with urllib.request.urlopen(url, timeout=20) as resp:
        if resp.status != 200:
            raise SystemExit(f"HTTP {resp.status} fetching {url}")
        return json.load(resp)

def get_local_tags(pkg: str) -> list[tuple[SemVer, str]]:
    """
    Get the versions in the local repo.

    Args:
        pkg: the package name.

    Returns:
        A list of all local tagged versions for the package arranged as a tuple of (SemVer, tag).
        Example:  "0.0.1" -> "curv-v0.0.1"
                  "0.0.2" -> "curv-v0.0.2"
                  ...
    """
    local_tags = subprocess.run(["git", "tag", "--list"], capture_output=True, text=True).stdout.splitlines()
    local_tags = [x for x in local_tags if f"{pkg}-v" in x]
    local_tags.sort(key=lambda x: SemVer.parse(x.replace(f"{pkg}-v", "")))
    ret: list[tuple[SemVer, str]] = []
    for tag in local_tags:
        ver = SemVer.parse(tag.replace(f"{pkg}-v", ""))
        ret.append((ver, f"{pkg}-v{ver}"))
        # print(f"{ver} -> {pkg}-v{ver}")
    return ret

def combine_iterators(pypi_versions: list[str], local_tags: list[tuple[SemVer, str]]) -> Iterator[Dict[str, Union[str, Optional[str], Optional[Tuple[SemVer, str]]]]]:
    """
    Combine PyPI versions and local tag versions into a single sorted iterator.

    Yields dictionaries containing version information from both sources.
    Each yielded dict has:
    - 'semver': the version string
    - 'pypi': version string if it exists in PyPI, None otherwise
    - 'local_tags': (SemVer, tag_string) tuple if it exists in local tags, None otherwise
    """
    # Create mappings for quick lookup
    pypi_set = set(pypi_versions)
    local_map = {str(semver): (semver, tag) for semver, tag in local_tags}

    # Get all unique version strings
    all_versions = pypi_set | set(local_map.keys())

    # Convert to SemVer objects for proper sorting
    semver_objects = []
    for ver_str in all_versions:
        try:
            semver_objects.append(SemVer.parse(ver_str))
        except ValueError:
            # Skip invalid version strings
            continue

    # Sort by SemVer precedence
    semver_objects.sort()

    # Yield detailed info for each version
    for semver in semver_objects:
        ver_str = str(semver)
        yield {
            'semver': ver_str,
            'pypi': ver_str if ver_str in pypi_set else None,
            'local_tags': local_map.get(ver_str)
        }

def main() -> None:
    ap = argparse.ArgumentParser(description="List SemVer releases for one of the PyPI packages in this repo.")
    ap.add_argument("-L", "--latest-only", action="store_true", help="Print only the latest SemVer")
    ap.add_argument("--include-yanked", action="store_true", help="Include versions where all files are yanked")
    ap.add_argument("pkg", metavar="PKG", nargs=1, help="Must be: 'curv', 'curvtools', or 'curvpyutils'", choices=["curv", "curvtools", "curvpyutils"])
    args = ap.parse_args()
    pkg = args.pkg[0]

    data = fetch_pypi_json(pkg)
    releases = data.get("releases", {})

    semvers: List[tuple[SemVer, str]] = []
    for ver_str, files in releases.items():
        if not files:
            continue
        if not args.include_yanked and all(f.get("yanked") for f in files):
            continue
        if not SEMVER_RE.match(ver_str):
            continue
        try:
            semvers.append((SemVer.parse(ver_str), ver_str))
        except ValueError:
            continue

    if not semvers:
        print(f"No SemVer releases found for {pkg}.", file=sys.stderr)
        sys.exit(2)

    semvers.sort()
    ordered: list[str] = [v for _, v in semvers]
    latest_pypi: str = ordered[-1]

    if args.latest_only:
        print(latest_pypi)
    else:
        table = Table(title=f"Versions for {pkg}", title_style="bold green")
        table.add_column("Version", justify="right")
        table.add_column("PyPI Published", justify="left")
        table.add_column("Local Tag", justify="left")
        local_tags: list[tuple[SemVer, str]] = get_local_tags(pkg)
        for version_info in combine_iterators(ordered, local_tags):
            semver: str = version_info['semver']
            pypi: Optional[str] = version_info['pypi'] if version_info['pypi'] else ""
            local: Optional[Tuple[SemVer, str]] = version_info['local_tags'][1] if version_info['local_tags'] else ""
            if version_info['local_tags'] is not None and version_info['pypi'] is not None:
                pypi_style = "bold green"
                local_style = "bold green"
            elif version_info['local_tags'] is not None and version_info['pypi'] is None:
                pypi_style = "bold green"
                local_style = "bold red"
            elif version_info['local_tags'] is None and version_info['pypi'] is not None:
                pypi_style = "bold red"
                local_style = "bold green"
            else:
                pypi_style = "bold red"
                local_style = "bold red"
            pypi_text = Text(pypi, style=pypi_style)
            local_text = Text(local, style=local_style)
            table.add_row(semver, pypi_text, local_text)
        console = Console()
        console.print(table)

if __name__ == "__main__":
    main()
