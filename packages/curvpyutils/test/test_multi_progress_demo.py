from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = [pytest.mark.e2e]


def test_multi_progress_demo_matches_expected(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    script = Path(__file__).resolve().parent / "multi_progress_demos.py"
    expected_path = (
        Path(__file__).resolve().parent
        / "test_vectors"
        / "expected"
        / "multi_progress_expected_demo_output.txt"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--seed",
            "12345",
            "--snapshot",
            "--width",
            "80",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    expected_output = expected_path.read_text()
    assert result.stdout == expected_output

