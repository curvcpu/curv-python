import os
import filecmp
from pathlib import Path
from types import TracebackType
from typing import Optional, IO, ContextManager

"""
Context manager that opens a file for writing and overwrites if and only if the new contents 
are different from the existing contents. If they aren't, the original file is not touched.

- A mutable flag dict can be passed in; its `value` key will be set to True if the original file
was overwritten.
- A `force_overwrite` option can be used to force even if there is no change.
- Original perms (mode bits) are restored to what they were on the original file.
- If the file does not exist, it is created (and the flag is set to True).

Example usage:

```python
path = "test.txt"
cm = open_write_iff_change(path, "w")
with cm as f:
    f.write("Hello, world!")

if cm.changed:
    print(f"File {path} was overwritten")
else:
    print(f"File {path} was not overwritten")
"""

class OpenOverwriteIffChange(ContextManager):
    def __init__(self, path: str | Path, mode: str, force_overwrite: bool = False):
        if "r" in mode:
            raise ValueError("read modes not allowed")

        self.path: Path = Path(path)
        self.mode: str = mode
        self._force_overwrite: bool = force_overwrite

        self._tmp: Optional[Path] = None
        self._fh: Optional[IO] = None
        self._orig_mode: Optional[int] = None
        self._changed: Optional[bool] = None  # public result, set in __exit__

    @property
    def changed(self) -> Optional[bool]:
        """True if file was overwritten, False if not, None before context exits."""
        return self._changed

    def __enter__(self) -> IO:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if self.path.exists():
            self._orig_mode = self.path.stat().st_mode

        rand = os.urandom(4).hex()
        tmpname = f".tmp_{self.path.name}.{rand}"
        self._tmp = self.path.parent / tmpname

        self._fh = open(self._tmp, self.mode)
        return self._fh

    def __exit__(self,
                exc_type: Optional[type],
                exc: Optional[BaseException],
                tb: Optional[TracebackType]) -> bool:
        try:
            if self._fh is not None:
                self._fh.flush()
                os.fsync(self._fh.fileno())
                self._fh.close()

            if exc_type is not None:
                if self._tmp and self._tmp.exists():
                    os.unlink(self._tmp)
                self._changed = None
                return False

            # Determine change
            if not self.path.exists() or self._force_overwrite:
                self._changed = True
            else:
                self._changed = not filecmp.cmp(self.path, self._tmp, shallow=False)

            if self._changed:
                os.replace(self._tmp, self.path)
                if self._orig_mode is not None:
                    os.chmod(self.path, self._orig_mode)
            else:
                os.unlink(self._tmp)

        finally:
            self._fh = None
            self._tmp = None
            self._orig_mode = None

        return False

def open_write_iff_change(path: str | Path, mode: str, force_overwrite: bool = False) -> OpenOverwriteIffChange:
    """
    Factory capturing caller's caller-scope for variable mutation

    Args:
        path: path to the file to possibly overwrite
        mode: mode to open the file in
        force_overwrite: Whether to force overwrite the file regardless of whether the new contents are the same as the existing contents.

    Returns:
        Context manager that opens the file for writing and overwrites if and only if the new contents would be different from the existing contents.
    """
    return OpenOverwriteIffChange(
        path, 
        mode, 
        force_overwrite=force_overwrite,
    )