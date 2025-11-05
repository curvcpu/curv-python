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
from datetime import datetime, timezone

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
    """
    Fetch the JSON metadata for the latest version of the package from PyPI.

    Args:
        pkg: the package name.

    Returns:
        A dictionary containing the JSON metadata for the latest version of the package.

    Notes:
        Format of the returned JSON is:
            {
            "info": {
                "author": "Mike Goelzer",
                "author_email": null,
                "bugtrack_url": null,
                "classifiers": [
                "Programming Language :: Python :: 3 :: Only"
                ],
                ...more info...
            "releases": {
                "0.0.1": [
                {
                    "comment_text": null,
                    ...more info...
                    "requires_python": ">=3.10",
                    "size": 1451,
                    "upload_time": "2025-10-31T20:22:42",
                    "upload_time_iso_8601": "2025-10-31T20:22:42.115058Z",
                    "url": "https://files.pythonhosted.org/packages/68/4f/52fceb19c379d9e397a201cde2fb8f0e1a1c3b9fd1c9e5c14accdf6218f1/curv-0.0.1-py3-none-any.whl",
                    "yanked": false,
                    "yanked_reason": null
                },
                {
                    ...more objects...
                }
                ]
                "0.1.3": [
                {
                    "comment_text": null,
                    ...more info...
                    "downloads": -1,
                    "filename": "curv-0.1.3-py3-none-any.whl",
                    "has_sig": false,
                    "md5_digest": "2a8cfa8af5ae84c4c68b97b0d81b6b37",
                    "packagetype": "bdist_wheel",
                    "python_version": "py3",
                    "requires_python": ">=3.10",
                    "size": 1451,
                    "upload_time": "2025-10-31T20:22:42",
                    "upload_time_iso_8601": "2025-10-31T20:22:42.115058Z",
                    "url": "https://files.pythonhosted.org/packages/68/4f/52fceb19c379d9e397a201cde2fb8f0e1a1c3b9fd1c9e5c14accdf6218f1/curv-0.0.1-py3-none-any.whl",
                    "yanked": false,
                    "yanked_reason": null
                },
                {
                    ...more objects...
                }
                ]
                ...more versions...
    """
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
        Example:  [(SemVer("0.0.1"), "curv-v0.0.1"), (SemVer("0.0.2"), "curv-v0.0.2"), ...]
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

def combine_iterators(pypi_semvers: List[tuple[SemVer, str, datetime]], local_tags: list[tuple[SemVer, str]]) -> Iterator[Dict[str, Union[str, Optional[str], Optional[Tuple[SemVer, str]], Optional[datetime]]]]:
    """
    Combine PyPI versions and local tag versions into a single sorted iterator.

    Yields dictionaries containing version information from both sources.
    Each yielded dict has:
    - 'semver': the version string
    - 'pypi': version string if it exists in PyPI, None otherwise
    - 'local_tags': (SemVer, tag_string) tuple if it exists in local tags, None otherwise
    - 'pypi_datetime': datetime when version was uploaded to PyPI, None if not available
    """
    # Create mappings for quick lookup
    pypi_map = {ver_str: dt for semver, ver_str, dt in pypi_semvers}
    local_map = {str(semver): (semver, tag) for semver, tag in local_tags}

    # Get all unique version strings
    all_versions = set(pypi_map.keys()) | set(local_map.keys())

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
            'pypi': ver_str if ver_str in pypi_map else None,
            'local_tags': local_map.get(ver_str),
            'pypi_datetime': pypi_map.get(ver_str)
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

    semvers: List[tuple[SemVer, str, datetime]] = []
    for ver_str, files in releases.items():
        if not files:
            continue
        if not args.include_yanked and all(f.get("yanked") for f in files):
            continue
        if not SEMVER_RE.match(ver_str):
            continue
        try:
            try:
                dt = datetime.fromisoformat(files[0].get("upload_time"))
            except:
                dt = None
            semvers.append((SemVer.parse(ver_str), ver_str, dt))
        except ValueError:
            continue

    if not semvers:
        print(f"No SemVer releases found for {pkg}.", file=sys.stderr)
        sys.exit(2)

    semvers.sort()
    latest_pypi: str = semvers[-1][1]

    def format_datetime(dt: Optional[datetime]) -> str:
        if dt is not None:
            # Assume PyPI datetime is UTC if naive, convert to local timezone
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            local_dt = dt.astimezone()
            tz_name = local_dt.tzname()
            return local_dt.strftime(f"%Y-%m-%d %I:%M%p").lower() + " " + local_dt.strftime(f"{tz_name}")
        else:
            return ""

    if args.latest_only:
        print(latest_pypi)
    else:
        table = Table(title=f"Versions for {pkg}", title_style="bold green")
        table.add_column("Version Number", justify="left", no_wrap=False)
        table.add_column("PyPI Published", justify="left", no_wrap=False)
        table.add_column("PyPI Timestamp", justify="left", no_wrap=False)
        table.add_column("Local Tag", justify="left", no_wrap=False)
        local_tags: list[tuple[SemVer, str]] = get_local_tags(pkg)
        for version_info in combine_iterators(semvers, local_tags):
            semver: str = version_info['semver']
            pypi: Optional[str] = version_info['pypi'] if version_info['pypi'] else ""
            local: Optional[Tuple[SemVer, str]] = version_info['local_tags'][1] if version_info['local_tags'] else ""
            pypi_datetime = format_datetime(version_info['pypi_datetime'])

            # coloration if there's a mismatch between local and PyPI tags
            pypi_style = "white"; local_style = "white"
            if version_info['local_tags'] is not None and version_info['pypi'] is not None:
                pass
            elif version_info['local_tags'] is not None and version_info['pypi'] is None:
                local_style = "bold red"
            elif version_info['local_tags'] is None and version_info['pypi'] is not None:
                pypi_style = "bold red"
            else:
                pypi_style = "bold red"
                local_style = "bold red"
            
            # apply styles and add row
            pypi_text = Text(pypi, style=pypi_style)
            pypi_datetime_text = Text(pypi_datetime, style=pypi_style)
            local_text = Text(local, style=local_style)
            table.add_row(semver, pypi_text, pypi_datetime_text, local_text)
        console = Console()
        console.print(table)

if __name__ == "__main__":
    main()
