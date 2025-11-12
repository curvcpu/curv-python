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
import os
import urllib.request
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Set, Tuple, Union
from enum import Flag, Enum, auto
from rich.console import Console
from rich.table import Table
from rich.text import Text
import subprocess
from datetime import datetime, timezone

class DateTime(datetime):
    class TsFormat(Enum):
        NONE = "none"
        UTC = "utc"
        EPOCH = "epoch"
        LOCAL = "local"

    def localformat(self) -> str:
        if self.tzinfo is None:
            self = self.replace(tzinfo=timezone.utc)
        local_dt = self.astimezone()
        tz_name = local_dt.tzname()
        return local_dt.strftime(f"%Y-%m-%d %I:%M%p").lower() + " " + local_dt.strftime(f"{tz_name}")
    
    def formatted_str(self, ts_format: 'DateTime.TsFormat') -> str:
        if ts_format == DateTime.TsFormat.NONE:
            return self.isoformat()
        elif ts_format == DateTime.TsFormat.UTC:
            return self.isoformat()
        elif ts_format == DateTime.TsFormat.EPOCH:
            return str(self.timestamp())
        elif ts_format == DateTime.TsFormat.LOCAL:
            return self.localformat()
        else:
            raise ValueError(f"invalid ts_format: {ts_format}")

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
    (?:[-|\.](?P<prerelease>(?:[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)))?
    (?:[+|\.](?P<build>(?:[0-9A-Za-z\?-]+(?:\.[0-9A-Za-z\.\?-]+)*)))?
    $
    """,
    re.VERBOSE,
)

def test_semver_re() -> None:
    assert SEMVER_RE.match("1.2.3") is not None
    assert SEMVER_RE.match("1.2.3-alpha.1") is not None
    assert SEMVER_RE.match("0.1.14-1+g0e71b7a.d20251112") is not None
    assert SEMVER_RE.match("0.0.1-0-g49d7b59") is not None
    assert SEMVER_RE.match("0.1.5-0-g30ae0f3") is not None
    assert SEMVER_RE.match("0.0.0-0+g????????") is not None
    print("✔️ semver-re test passed")

# git-describe regex examples (prefix already stripped):
# - 0.1.8-0-g2205bf8 -> major=0, minor=1, patch=8, prerelease=['0'], build='2205bf8'
# - 2.3.4-12-gABCDEF0 -> major=2, minor=3, patch=4, prerelease=['12'], build='ABCDEF0'
GIT_DESCRIBE_RE = re.compile(
    r"""
    ^
    (?P<major>0|[1-9]\d*)\.
    (?P<minor>0|[1-9]\d*)\.
    (?P<patch>0|[1-9]\d*)
    [-|\.]
    (?P<commits>\d+)
    [-|+]g
    (?P<build>[0-9a-fA-F\.\?]+)
    $
    """,
    re.VERBOSE,
)

def test_git_describe_re() -> None:
    assert GIT_DESCRIBE_RE.match("0.1.14-1+g0e71b7a.d20251112") is not None
    assert GIT_DESCRIBE_RE.match("0.0.1-0-g49d7b59") is not None
    assert GIT_DESCRIBE_RE.match("0.1.5-0-g30ae0f3") is not None
    assert GIT_DESCRIBE_RE.match("0.0.0-0+g????????") is not None
    print("✔️ git-describe-re test passed")

@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: Optional[List[str]]  # identifiers (split on '.')
    build: Optional[str]             # ignored in ordering
    # These fields are NOT part of the SemVer but used for conversion to string
    pkg: Optional[str]               # package name
    dt: Optional[DateTime]           # creation DateTime

    @staticmethod
    def parse(version_str: str, pkg: Optional[str] = None, dt: Optional[DateTime|datetime|str] = None) -> "SemVer":
        s = version_str[len(f"{pkg}-v"):] if version_str.startswith(f"{pkg}-v") else version_str
        m = SEMVER_RE.match(s)
        if not m:
            raise ValueError(f"not semver: {s}")
        major = int(m.group("major"))
        minor = int(m.group("minor"))
        patch = int(m.group("patch"))
        pr = m.group("prerelease")
        build = m.group("build")
        dt = DateTime.fromisoformat(dt) if isinstance(dt, str) else dt
        return SemVer(major, minor, patch, pr.split(".") if pr else None, build, pkg, dt)

    @staticmethod
    def parse_git_describe(version_str: str, pkg: str, dt: Optional[DateTime|datetime|str] = None) -> "SemVer":
        """
        Parse a git-describe-like string such as 'curv-v0.1.8-0-g2205bf8' by
        first stripping the provided pkg name (e.g., 'curv'), then extracting
        components from '0.1.8-0-g2205bf8'. The number after the patch is
        returned as a single prerelease identifier, and the hash becomes build.
        """
        s = version_str[len(f"{pkg}-v"):] if version_str.startswith(f"{pkg}-v") else version_str
        m = GIT_DESCRIBE_RE.match(s)
        if not m:
            raise ValueError(f"not git-describe: {s}")
        major = int(m.group("major"))
        minor = int(m.group("minor"))
        patch = int(m.group("patch"))
        commits_since = m.group("commits")
        build = m.group("build")
        prerelease = [commits_since] if commits_since is not None else None
        dt = DateTime.fromisoformat(dt) if isinstance(dt, str) else dt
        return SemVer(major, minor, patch, prerelease, build, pkg, dt)

    def _precedence_key(self) -> Tuple:
        """
        SemVer precedence:
          (major, minor, patch, release_marker, prerelease_key, datetime)
        where release_marker = 1 for final releases (so finals > prerelease),
        and prerelease_key compares identifiers per spec:
          - numeric ids compare numerically and are LOWER than non-numeric
          - lexicographic for non-numeric
          - if equal prefix, longer list is HIGHER precedence
        and datetime is the creation datetime in UTC.
        """
        if self.prerelease is None:
            # Finals sort after any prerelease of same M.m.p
            return (self.major, self.minor, self.patch, 1, self.dt)
        ids = []
        for ident in self.prerelease:
            if ident.isdigit():
                ids.append((0, int(ident)))   # numeric < non-numeric
            else:
                ids.append((1, ident))
        # include length so longer prerelease list > shorter when prefix equal
        return (self.major, self.minor, self.patch, 0, tuple(ids), len(self.prerelease), self.dt)

    def __lt__(self, other: "SemVer") -> bool:  # type: ignore[override]
        return self._precedence_key() < other._precedence_key()
    
    def __hash__(self) -> int:
        """
        Hash based on all fields. Converts prerelease list to tuple for hashing,
        and handles None values appropriately.
        """
        prerelease_tuple = tuple(self.prerelease) if self.prerelease is not None else None
        dt_hash = self.dt.timestamp() if self.dt is not None else None
        return hash((self.major, self.minor, self.patch, prerelease_tuple, self.build, self.pkg, dt_hash))
    
    @dataclass(frozen=True)
    class Format(Enum):
        GIT = "GIT"
        SEMVER = "SEMVER"
    
    class Fields(Flag):
        NONE        = 0          # must be zero so X | NONE == X
        PKG         = auto()     # 1
        BUILD       = auto()     # 2
        PRERELEASE  = auto()     # 4
        ALL         = PKG | BUILD | PRERELEASE

    def __post_init__(self):
        # sanity check
        fields = self.Fields.PKG | self.Fields.BUILD
        assert self.Fields.PKG in fields
        assert not (self.Fields.PRERELEASE in fields)
        assert self.Fields.NONE | self.Fields.BUILD == self.Fields.BUILD
        assert self.Fields.BUILD in (fields & self.Fields.BUILD)        # equivalent membership test
        assert ((fields & self.Fields.BUILD) == self.Fields.BUILD)      # equivalent membership test
        assert ((fields & self.Fields.PKG) == self.Fields.PKG)          # equivalent membership test
        assert ((fields & self.Fields.PRERELEASE) == self.Fields.NONE)  # equivalent membership test

        fields = self.Fields.ALL
        assert self.Fields.PKG in fields
        assert self.Fields.BUILD in fields
        assert self.Fields.PRERELEASE in fields
     
    def get_full_str(self, format: 'SemVer.Format' = 'SemVer.Format.SEMVER', fields: 'SemVer.Fields' = 'SemVer.Fields.ALL') -> str:
        if format == self.Format.GIT:
            prerelease_str = f'.dev{len(self.prerelease)}' if self.prerelease and self.Fields.PRERELEASE in fields else ''
            build_str = (f'+g{self.build}' if self.build and self.Fields.BUILD in fields else '')
        else:
            prerelease_str = '-' + '.'.join(self.prerelease) if self.prerelease and self.Fields.PRERELEASE in fields else ''
            build_str = (f'+{self.build}' if self.build and self.Fields.BUILD in fields else '')
        if not self.Fields.PKG in fields:
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

def git_describe_tag_long(short_tag: str, cwd: Optional[str] = None, pkg: Optional[str] = None) -> str:
    """
    Runs `git describe --tags --long {short_tag}` and returns the git describe
    long tag string, e.g., "curv-v0.0.1" -> "curv-v0.0.1-0-g1234567".
    
    Args:
        short_tag: the short tag string to describe (e.g., "curv-v0.0.1")
        cwd: the current working directory (default: current directory)
        pkg: if provided, we'll only return the long tag string prefixed with `pkg-v*`
    
    Returns:
        The long tag string (e.g., "curv-v0.0.1-0-g1234567")
    """
    p = subprocess.run(
        ["git", "describe", "--tags", "--long", short_tag],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
    )
    if p.returncode not in (0, None):
        raise subprocess.CalledProcessError(p.returncode, p.args, p.stderr)
    if pkg is not None and not p.stdout.startswith(f"{pkg}-v"):
        return f"{short_tag}-0+g????????"
    return p.stdout.strip()

def get_local_tags3(pkg: str, cwd: Optional[str] = None) -> List[SemVer]:
    """
    Get the local git tags for the package, returning a List of SemVer's with package name
    and creation datetime fields set.
    """
    # git tag --list '{pkg}-v*' --format '%(refname:short) %(creatordate:iso8601-strict)'
    # returns a list of lines like:
    #   curv-v0.0.1 2025-10-31T14:20:48-06:00
    #   curv-v0.1.0 2025-10-31T13:35:34-06:00
    #   curv-v0.1.1 2025-10-31T13:35:34-06:00
    #   ...
    p = subprocess.run(
        ["git", "tag", "--list", f"{pkg}-v*", "--format", "%(refname:short) %(creatordate:iso8601-strict)"],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if p.returncode not in (0, None):
        raise subprocess.CalledProcessError(p.returncode, p.args, p.stderr)
    lines = [ln for ln in (p.stdout.splitlines() if p.stdout else []) if ln]
    semvers: List[SemVer] = []
    for ln in lines:
        # short tag is like "curv-v0.0.1"
        # dt_str is like "2025-10-31T14:20:48-06:00" (UTC)
        # long tag is like "curv-v0.0.1-0-g1234567"
        short_tag, dt_str = ln.split(" ")
        long_tag = git_describe_tag_long(short_tag, cwd=cwd, pkg=pkg)
        semvers.append(SemVer.parse_git_describe(long_tag, pkg=pkg, dt=dt_str))
    if semvers:
        semvers.sort()
    return semvers if semvers else []

def combine_iterators(pypi_semvers: List[SemVer], local_tags: List[SemVer], version_py_semver: Optional[SemVer]) -> Iterator[Tuple[str, Dict[str, [Optional[SemVer]]]]]:
    """
    Combine PyPI versions and local tag versions into a single sorted iterator.

    Yields a tuple of (version string, dictionary with keys 'pypi', 'tags' and '_version_py').
    Each of those keys is a SemVer object if it exists, None otherwise.
    """

    # Create mappings for quick lookup
    pypi_map = {str(semver): semver for semver in pypi_semvers}
    tags_map = {str(semver): semver for semver in local_tags}
    version_py_map = {str(semver): semver for semver in [version_py_semver] if version_py_semver is not None}

    # Get all unique version strings
    all_version_keys = set(pypi_map.keys()) | set(tags_map.keys()) | set(version_py_map.keys())

    # Convert to SemVer objects for proper sorting
    semver_version_objects: List[SemVer] = []
    for ver_str in all_version_keys:
        try:
            semver_version_objects.append(pypi_map[ver_str] if ver_str in pypi_map else tags_map[ver_str] if ver_str in tags_map else version_py_map[ver_str])
        except ValueError:
            # Skip invalid version strings
            continue
    semver_version_objects.sort()

    # Yield detailed info for each version
    for semver in semver_version_objects:
        yield (semver, {
            'pypi': pypi_map[str(semver)] if str(semver) in pypi_map else None,
            'tags': tags_map[str(semver)] if str(semver) in tags_map else None,
            '_version_py': version_py_map[str(semver)] if str(semver) in version_py_map else None,
        })

def get_pypi_semvers(pkg, args) -> List[SemVer]:
    data = fetch_pypi_json(pkg)
    releases = data.get("releases", {})
    
    semvers: List[SemVer] = []
    for ver_str, files in releases.items():
        if not files:
            continue
        if not args.include_yanked and all(f.get("yanked") for f in files):
            continue
        if not SEMVER_RE.match(ver_str):
            continue
        try:
            try:
                upload_time_str = files[0].get("upload_time")
                dt = DateTime.fromisoformat(upload_time_str).replace(tzinfo=timezone.utc)
            except:
                dt = None
            semvers.append(SemVer.parse(ver_str, pkg=pkg, dt=dt))
        except ValueError:
            continue
    
    if not semvers:
        print(f"No SemVer releases found for {pkg}.", file=sys.stderr)
        sys.exit(2)
    
    semvers.sort()
    return semvers

def get_version_py_semver(pkg: str) -> SemVer:
    """
    Get the version info from the package's _version.py file.
    """
    version_py_path = f"packages/{pkg}/src/{pkg}/_version.py"
    import runpy, re
    result = runpy.run_path(version_py_path)
    vt = result["__version_tuple__"]
    git_describe_str = (
        ".".join(str(x) for x in vt[:3] if x is not None)
        + ("-" + re.sub(r"[A-Za-z]+", "", str(vt[3])) if vt[3] is not None else "")
        + ("+" + str(vt[4]) if len(vt) > 4 and vt[4] is not None else "")
    )
    mtime_epoch: float = os.path.getmtime(version_py_path)
    mtime_dt: DateTime = DateTime.fromtimestamp(mtime_epoch, timezone.utc)
    return SemVer.parse_git_describe(version_str=git_describe_str, pkg=pkg, dt=mtime_dt)

def main() -> None:

    ap = argparse.ArgumentParser(description="List SemVer for PyPI releases, git tags or _version.py files in this repo")
    ap.add_argument("--include-yanked", action="store_true", help="include versions where all files are yanked")
    ap.add_argument("--include-commit-hash", "-b", action="store_true", help="Include the commit hash in git tag string")
    ap.add_argument("--include-pkg-name", "-p", action="store_true", help="Include the package name prefix in git tag string")
    ap.add_argument("--include-ts", "-ts", dest="include_ts", type=str, choices=[fmt.value for fmt in DateTime.TsFormat], default=DateTime.TsFormat.NONE.value, help="Include the timestamp; for -L/-G/-V, replaces the version string with the timestamp in this format")
    ap.add_argument("pkg", metavar="PKG", nargs=1, help="Must be: 'curv', 'curvtools', or 'curvpyutils'", choices=["curv", "curvtools", "curvpyutils"])

    class SourceType(Enum):
        PYPI = "PYPI"
        GIT_TAGS = "GIT_TAGS"
        VERSION_PY = "VERSION_PY"
        NONE = "NONE"

    # Show these as their own titled group in help output
    type_section = ap.add_argument_group("Show only the latest version from")
    latest_source_group = type_section.add_mutually_exclusive_group()
    latest_source_group.add_argument("--latest-pypi", "-L", dest="latest_only", action="store_const", const=SourceType.PYPI, help="Print the latest PyPI published version")
    latest_source_group.add_argument("--latest-git-tag", "-G", dest="latest_only", action="store_const", const=SourceType.GIT_TAGS, help="Print the latest git tag")
    latest_source_group.add_argument("--latest-version-py", "-V", dest="latest_only", action="store_const", const=SourceType.VERSION_PY, help="Print the latest version info based on the package's _version.py file")
    ap.set_defaults(latest_only=SourceType.NONE)

    args = ap.parse_args()
    ts_format = DateTime.TsFormat(args.include_ts)
    pkg = args.pkg[0]

    # args-aware semver->str function
    display_fields = SemVer.Fields.NONE | (SemVer.Fields.PKG if args.include_pkg_name else SemVer.Fields.NONE) | (SemVer.Fields.BUILD | SemVer.Fields.PRERELEASE if args.include_commit_hash else SemVer.Fields.NONE)
    get_tag_str = lambda semver: semver.get_full_str(format=SemVer.Format.GIT, fields=display_fields)
    get_pypi_ver_str = lambda semver: semver.get_full_str(format=SemVer.Format.SEMVER, fields=SemVer.Fields.NONE) # PyPI only has major.minor.patch
    get_version_py_str = lambda semver: semver.get_full_str(format=SemVer.Format.GIT, fields=display_fields)

    pypi_semvers = get_pypi_semvers(pkg, args)
    latest_pypi: str = get_pypi_ver_str(pypi_semvers[-1])
    latest_pypi_dt: DateTime = pypi_semvers[-1].dt.formatted_str(ts_format)

    git_tag_semvers = get_local_tags3(pkg)
    latest_git_tag: str = get_tag_str(git_tag_semvers[-1])
    latest_git_tag_dt: DateTime = git_tag_semvers[-1].dt.formatted_str(ts_format)

    version_py_semver = get_version_py_semver(pkg)
    latest_version_py: str = get_version_py_str(version_py_semver)
    latest_version_py_dt: DateTime = version_py_semver.dt.formatted_str(ts_format)

    if args.latest_only == SourceType.PYPI:
        if ts_format != DateTime.TsFormat.NONE:
            print(f"{latest_pypi_dt}")
        else:
            print(latest_pypi)
    elif args.latest_only == SourceType.GIT_TAGS:
        if ts_format != DateTime.TsFormat.NONE:
            print(f"{latest_git_tag_dt}")
        else:
            print(latest_git_tag)
    elif args.latest_only == SourceType.VERSION_PY:
        if ts_format != DateTime.TsFormat.NONE:
            print(f"{latest_version_py_dt}")
        else:
            print(latest_version_py)
    else:
        table = Table(title=f"Versions for {pkg}", title_style="bold green")
        table.add_column("Version", justify="left", no_wrap=False)
        table.add_column("PyPI", justify="left", no_wrap=False)
        if ts_format != DateTime.TsFormat.NONE:
            table.add_column(f"PyPI Timestamp ({ts_format.value})", justify="left", no_wrap=False)
        table.add_column("Tag", justify="left", no_wrap=False)
        if ts_format != DateTime.TsFormat.NONE:
            table.add_column(f"Tag Timestamp ({ts_format.value})", justify="left", no_wrap=False)
        if args.include_commit_hash:
            table.add_column("git describe --long", justify="left", no_wrap=False)
        table.add_column("_version.py", justify="left", no_wrap=False)
        if ts_format != DateTime.TsFormat.NONE:
            table.add_column(f"_version.py Timestamp ({ts_format.value})", justify="left", no_wrap=False)
        
        for semver, version_info in combine_iterators(pypi_semvers, git_tag_semvers, version_py_semver):
            ver_str: str = str(semver)
            pypi_ver: Optional[str] = get_pypi_ver_str(version_info['pypi']) if version_info['pypi'] else ""
            tag_str: str = version_info['tags'].get_full_str(fields=SemVer.Fields.PKG) if version_info['tags'] else ""
            pypi_datetime = version_info['pypi'].dt.formatted_str(ts_format) if version_info['pypi'] is not None else ""
            tag_datetime = version_info['tags'].dt.formatted_str(ts_format) if version_info['tags'] is not None else ""
            version_py_datetime = version_info['_version_py'].dt.formatted_str(ts_format) if version_info['_version_py'] is not None else ""
            
            # coloration if there's a mismatch between local and PyPI tags
            pypi_style = "bold red" if version_info['pypi'] is not None and version_info['tags'] is None else "white"
            tags_style = "bold red" if version_info['tags'] is not None and version_info['pypi'] is None else "white"
            version_py_style = "bold red" if version_info['_version_py'] is not None and version_info['pypi'] is None else "white"
            
            # apply styles and add row
            pypi_text = Text(pypi_ver, style=pypi_style)
            pypi_datetime_text = Text(pypi_datetime, style=pypi_style)
            tag_text = Text(tag_str, style=tags_style)
            tag_datetime_text = Text(tag_datetime, style=tags_style)
            version_py_text = Text(get_version_py_str(version_info['_version_py']) if version_info['_version_py'] else "", style=version_py_style)
            version_py_datetime_text = Text(version_py_datetime, style=version_py_style)

            add_row_args = [ver_str, pypi_text]
            if ts_format != DateTime.TsFormat.NONE:
                add_row_args.append(pypi_datetime_text)
            add_row_args.append(tag_text)
            if ts_format != DateTime.TsFormat.NONE:
                add_row_args.append(tag_datetime_text)
            if args.include_commit_hash:
                build_text_tags = Text(version_info['tags'].get_full_str(format=SemVer.Format.GIT, fields=SemVer.Fields.ALL) if version_info['tags'] else "", style=tags_style)
                add_row_args.append(build_text_tags)
            add_row_args.append(version_py_text)
            if ts_format != DateTime.TsFormat.NONE:
                add_row_args.append(version_py_datetime_text)
            table.add_row(*add_row_args)
        console = Console()
        console.print(table)

if __name__ == "__main__":
    main()
