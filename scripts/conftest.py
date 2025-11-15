"""
Ensure local packages are importable when running pytest without editable installs.
"""
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
src_paths = [
    repo_root / "scripts" / "publish-tools" / "src",
]
for p in src_paths:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


