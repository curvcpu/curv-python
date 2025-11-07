#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["rich>=13"]
# ///
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterator, List, Optional, Tuple, Union
from rich.console import Console
from rich.table import Table
from rich.text import Text
import subprocess
from datetime import datetime, timezone

# SemVer regex examples (1.2.3 with optional prerelease/build):
# - prerelease only: 1.2.3-alpha.1 -> prerelease='alpha.1', build=None
# - build only:      1.2.3+20130313144700 -> prerelease=None, build='20130313144700'
# - both:            1.2.3-beta+exp.sha.5114f85 -> prerelease='beta', build='exp.sha.5114f85'
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

# git-describe regex examples (prefix already stripped):
# - 0.1.8-0-g2205bf8 -> major=0, minor=1, patch=8, prerelease=['0'], build='2205bf8'
# - 2.3.4-12-gABCDEF0 -> major=2, minor=3, patch=4, prerelease=['12'], build='ABCDEF0'
GIT_DESCRIBE_RE = re.compile(
    r"""
    ^
    (?P<major>0|[1-9]\d*)\.
    (?P<minor>0|[1-9]\d*)\.
    (?P<patch>0|[1-9]\d*)
    -
    (?P<commits>\d+)
    -g
    (?P<build>[0-9a-fA-F]+)
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
    pkg: Optional[str]               # package name

    @staticmethod
    def parse(s: str, pkg: Optional[str] = None) -> "SemVer":
        m = SEMVER_RE.match(s)
        if not m:
            raise ValueError(f"not semver: {s}")
        major = int(m.group("major"))
        minor = int(m.group("minor"))
        patch = int(m.group("patch"))
        pr = m.group("prerelease")
        build = m.group("build")
        return SemVer(major, minor, patch, pr.split(".") if pr else None, build, pkg)

    @staticmethod
    def parse_git_describe(s: str, pkg: str) -> "SemVer":
        """
        Parse a git-describe-like string such as 'curv-v0.1.8-0-g2205bf8' by
        first stripping the provided prefix (e.g., 'curv-v'), then extracting
        components from '0.1.8-0-g2205bf8'. The number after the patch is
        returned as a single prerelease identifier, and the hash becomes build.
        """
        prefix = f"{pkg}-v"
        if s.startswith(prefix):
            s2 = s[len(prefix):]
        else:
            s2 = s
        m = GIT_DESCRIBE_RE.match(s2)
        if not m:
            raise ValueError(f"not git-describe: {s}")
        major = int(m.group("major"))
        minor = int(m.group("minor"))
        patch = int(m.group("patch"))
        commits_since = m.group("commits")
        build = m.group("build")
        prerelease = [commits_since] if commits_since is not None else None
        pkg = prefix.replace("-v", "")
        return SemVer(major, minor, patch, prerelease, build, pkg)

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
    
    def get_full_str(self, using_git_format: bool = False, omit_pkg_name: bool = False) -> str:
        if using_git_format:
            prerelease_str = f'.dev{len(self.prerelease)}' if self.prerelease else ''
            build_str = (f'+g{self.build}' if self.build else '')
        else:
            build_str = (f'+{self.build}' if self.build else '')
            prerelease_str = '-' + '.'.join(self.prerelease) if self.prerelease else ''
        if omit_pkg_name:
            return f"{self.major}.{self.minor}.{self.patch}{prerelease_str}{build_str}"
        else:
            return f"{self.pkg}-v{self.major}.{self.minor}.{self.patch}{prerelease_str}{build_str}"

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

def get_local_tags2(pkg: str, cwd: Optional[str] = None) -> List[tuple[SemVer, str]]:
    """
    Equivalent to:
        git tag --list '{pkg}-v*' | xargs -n1 git describe --tags --long
    but sorts the final lines in Python before returning.
    """
    # 1) git tag --list '{pkg}-v*'
    p1 = subprocess.Popen(
        ["git", "tag", "--list", f"{pkg}-v*"],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # 2) xargs -n1 git describe --tags --long  (stdin from p1)
    p2 = subprocess.Popen(
        ["xargs", "-n1", "git", "describe", "--tags", "--long"],
        cwd=cwd,
        stdin=p1.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if p1.stdout is not None:
        p1.stdout.close()

    out, err2 = p2.communicate()
    _, err1 = p1.communicate()

    if p1.returncode not in (0, None):
        raise subprocess.CalledProcessError(p1.returncode, p1.args, err1)
    if p2.returncode not in (0, None):
        raise subprocess.CalledProcessError(p2.returncode, p2.args, err2)

    lines = [ln for ln in (out.splitlines() if out else []) if ln]
    semvers: List[SemVer] = []
    for ln in lines:
        try:
            semvers.append(SemVer.parse_git_describe(ln, pkg))
        except ValueError:
            continue
    if semvers:
        semvers.sort()
    return [(semver, f"{pkg}-v{semver}") for semver in semvers] if semvers else []

# def get_local_tags(pkg: str) -> list[tuple[SemVer, str]]:
#     """
#     Get the versions in the local repo.
#
#     Args:
#         pkg: the package name.
#
#     Returns:
#         A list of all local tagged versions for the package arranged as a tuple of (SemVer, tag).
#         Example:  [(SemVer("0.0.1"), "curv-v0.0.1"), (SemVer("0.0.2"), "curv-v0.0.2"), ...]
#     """
#     local_tags = subprocess.run(["git", "tag", "--list"], capture_output=True, text=True).stdout.splitlines()
#     local_tags = [x for x in local_tags if f"{pkg}-v" in x]
#     local_tags.sort(key=lambda x: SemVer.parse(x.replace(f"{pkg}-v", "")))
#     ret: list[tuple[SemVer, str]] = []
#     for tag in local_tags:
#         ver = SemVer.parse(tag.replace(f"{pkg}-v", ""))
#         ret.append((ver, f"{pkg}-v{ver}"))
#         # print(f"{ver} -> {pkg}-v{ver}")
#     return ret

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
    ap = argparse.ArgumentParser(description="List SemVer releases for one of the PyPI packages or local git tags in this repo.")
    ap.add_argument("--include-yanked", action="store_true", help="Include versions where all files are yanked")
    # ap.add_argument("-L", "--latest-only", action="store_true", help="Print only the latest SemVer")
    ap.add_argument("--include-commit-hash", "-b", action="store_true", help="Include the commit hash in local tag string")
    ap.add_argument("--include-pkg-name", "-p", action="store_true", help="Include the package name prefix in local tag string")
    ap.add_argument("pkg", metavar="PKG", nargs=1, help="Must be: 'curv', 'curvtools', or 'curvpyutils'", choices=["curv", "curvtools", "curvpyutils"])

    class SourceType(Enum):
        PYPI = "PYPI"
        GIT_TAGS = "GIT_TAGS"
        NEITHER = "NEITHER"
    # Show these as their own titled group in help output
    type_section = ap.add_argument_group("Show only the latest version from")
    latest_source_group = type_section.add_mutually_exclusive_group()
    latest_source_group.add_argument("--latest-pypi", "-L", dest="latest_only", action="store_const", const=SourceType.PYPI, help="Print only the latest PyPI published version")
    latest_source_group.add_argument("--latest-git-tag", "-G", dest="latest_only", action="store_const", const=SourceType.GIT_TAGS, help="Print only the latest local git tag")
    ap.set_defaults(latest_only=SourceType.NEITHER)

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

    local_tags: list[tuple[SemVer, str]] = get_local_tags2(pkg)
    if args.include_commit_hash and args.include_pkg_name:
        # includes package name and version and build hash
        latest_local_tag: str = local_tags[-1][0].get_full_str(using_git_format=True, omit_pkg_name=False)
    elif args.include_pkg_name:
        # includes package name and version and git tag
        latest_local_tag: str = local_tags[-1][1]
    elif args.include_commit_hash:
        # includes only version and build hash
        latest_local_tag: str = local_tags[-1][0].get_full_str(using_git_format=True, omit_pkg_name=True)
    else:
        # includes only version
        latest_local_tag: str = str(local_tags[-1][0])

    if args.latest_only == SourceType.PYPI:
        print(latest_pypi)
    elif args.latest_only == SourceType.GIT_TAGS:
        print(latest_local_tag)
    else:
        def get_local_tag_str(combined_iter_info: dict[str, Union[str, Optional[Tuple[SemVer, str]], Optional[datetime]]], include_build: bool = False, include_pkg_name: bool = False) -> str:
            """
            Get the local tag string for the combined iterator element, with or without the commit hash.

            Args:
                combined_iter_info: the combined iterator element in loop below.
                include_build: whether to include the commit hash in the local tag string.
                include_pkg_name: whether to include the package name in the local tag string.
            
            Returns:
                The local git tag string for the combined iterator element.
            """
            if 'local_tags' in combined_iter_info and combined_iter_info['local_tags'] is not None:
                if include_build and include_pkg_name:
                    # includes package name and version and build hash
                    local = combined_iter_info['local_tags'][0].get_full_str(using_git_format=True, omit_pkg_name=False)
                elif include_build:
                    # includes version and build hash
                    local = combined_iter_info['local_tags'][0].get_full_str(using_git_format=True, omit_pkg_name=True)
                elif include_pkg_name:
                    # includes package name and version
                    local = combined_iter_info['local_tags'][1]
                else:
                    # includes only version
                    local = str(combined_iter_info['local_tags'][0])
            else:
                local = ""
            return local

        table = Table(title=f"Versions for {pkg}", title_style="bold green")
        table.add_column("Version", justify="center", no_wrap=False)
        table.add_column("PyPI Publish", justify="center", no_wrap=False)
        table.add_column("PyPI Timestamp", justify="left", no_wrap=False)
        table.add_column("Local Tag", justify="left", no_wrap=False)
        if args.include_commit_hash:
            table.add_column("Tag (git describe)", justify="left", no_wrap=False)
        
        #local_tags: list[tuple[SemVer, str]] = get_local_tags(pkg)
        for version_info in combine_iterators(semvers, local_tags):
            semver: str = version_info['semver']
            pypi: Optional[str] = version_info['pypi'] if version_info['pypi'] else ""
            local: str = get_local_tag_str(version_info, include_build=False, include_pkg_name=True)
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
            if args.include_commit_hash:
                if args.include_pkg_name:
                    build_text = Text(get_local_tag_str(version_info, include_build=True, include_pkg_name=True), style=local_style)
                else:
                    build_text = Text(get_local_tag_str(version_info, include_build=True, include_pkg_name=False), style=local_style)
                table.add_row(semver, pypi_text, pypi_datetime_text, local_text, build_text)
            else:
                table.add_row(semver, pypi_text, pypi_datetime_text, local_text)
        console = Console()
        console.print(table)

if __name__ == "__main__":
    main()
