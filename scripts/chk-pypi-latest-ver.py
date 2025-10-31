#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from typing import List, Optional, Tuple

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

def fetch_pypi_json(pkg: str) -> dict:
    url = f"https://pypi.org/pypi/{pkg}/json"
    with urllib.request.urlopen(url, timeout=20) as resp:
        if resp.status != 200:
            raise SystemExit(f"HTTP {resp.status} fetching {url}")
        return json.load(resp)

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
    ordered = [v for _, v in semvers]
    latest = ordered[-1]

    if args.latest_only:
        print(latest)
    else:
        for v in ordered:
            print(v)

if __name__ == "__main__":
    main()
