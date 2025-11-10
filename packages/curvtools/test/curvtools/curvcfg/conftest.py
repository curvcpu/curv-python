import os
import sys
import subprocess
from pathlib import Path


def _compute_repo_root() -> str:
    try:
        cp = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return cp.stdout.strip()
    except Exception:
        # Fallback: walk up to nearest .git
        p = Path(__file__).resolve()
        for parent in p.parents:
            if (parent / ".git").exists():
                return str(parent)
        return str(Path(__file__).resolve().parents[5])


def pytest_sessionstart(session):
    # Ensure sibling helper is importable from subdirs
    this_dir = Path(__file__).resolve().parent
    if str(this_dir) not in sys.path:
        sys.path.insert(0, str(this_dir))

    REL_FAKE_CURV_ROOT = "packages/curvtools/test/curvtools/curvcfg/fake_curv_root"

    repo_root = _compute_repo_root()
    fake_root = os.path.join(repo_root, REL_FAKE_CURV_ROOT)
    os.environ.setdefault("CURV_ROOT_DIR", fake_root)
    os.environ.setdefault("CURV_FAKE_ROOT_REL", REL_FAKE_CURV_ROOT)
