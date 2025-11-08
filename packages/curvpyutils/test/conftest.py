"""
Ensure local packages are importable when running pytest without editable installs.
"""
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[3]
src_paths = [
    repo_root / "packages" / "curvtools" / "src",
    repo_root / "packages" / "curvpyutils" / "src",
    repo_root / "packages" / "curv" / "src",
]
for p in src_paths:
    ps = str(p)
    if ps not in sys.path:
        sys.path.insert(0, ps)


