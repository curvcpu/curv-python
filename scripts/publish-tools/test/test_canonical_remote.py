from __future__ import annotations
import pytest
from typing import Iterable, List, Tuple, Optional
from canonical_remote import find_canonical_remote, DEFAULT_HOSTNAME, DEFAULT_ORG, DEFAULT_REPO

# Test cases as module-level global variable
TEST_CASES: List[Tuple[str, Iterable[str], Optional[str]]] = [
    (
        "different remotes for fetch/push (should fail)",
        [
            "origin\tgit@github.com:curvcpu/curv-python.git (fetch)",
            "xxxx\tgit@github.com:curvcpu/curv-python.git (push)",
        ],
        None,
    ),
    (
        "single remote, ssh, both directions (origin, should pass)",
        [
            "origin\tgit@github.com:curvcpu/curv-python.git (fetch)",
            "origin\tgit@github.com:curvcpu/curv-python.git (push)",
        ],
        "origin",
    ),
    (
        "single remote, https, both directions (upstream, should pass)",
        [
            "upstream\thttps://github.com/curvcpu/curv-python.git (fetch)",
            "upstream\thttps://github.com/curvcpu/curv-python.git (push)",
        ],
        "upstream",
    ),
    (
        "no canonical remote (should fail)",
        [
            "origin\tgit@github.com:someoneelse/other.git (fetch)",
            "origin\tgit@github.com:someoneelse/other.git (push)",
        ],
        None,
    ),
    (
        "remote has canonical fetch but non-canonical push (should fail)",
        [
            "origin\tgit@github.com:curvcpu/curv-python.git (fetch)",
            "origin\tgit@github.com:curvcpu/other-repo.git (push)",
        ],
        None,
    ),
    (
        "remote has canonical push but non-canonical fetch (should fail)",
        [
            "origin\tgit@github.com:curvcpu/other-repo.git (fetch)",
            "origin\tgit@github.com:curvcpu/curv-python.git (push)",
        ],
        None,
    ),
]


@pytest.mark.parametrize(
    "desc,lines,expected",
    TEST_CASES,
    ids=[case[0] for case in TEST_CASES]  # Use descriptions as test IDs
)
def test_canonical_remote(desc: str, lines: Iterable[str], expected: Optional[str]) -> None:
    """Test finding canonical remote for various git remote configurations."""
    hostname = "github.com"
    org = "curvcpu"
    repo = "curv-python"

    if expected is None:
        # Test case expects failure
        with pytest.raises(Exception):
            find_canonical_remote(hostname, org, repo, lines)
    else:
        # Test case expects success
        result = find_canonical_remote(hostname, org, repo, lines)
        assert result == expected
