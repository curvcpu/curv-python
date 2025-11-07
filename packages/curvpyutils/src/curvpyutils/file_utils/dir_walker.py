from enum import Enum
import os
import inspect
from typing import Callable
from pathlib import Path

class DirWalker:
    """
    Class that finds files matching certain criteria starting in `sub_dir` and continuing to
    walk up the directory tree until it reaches `root_dir`.  (root_dir must be the parent of sub_dir.)

    The criterion is specified by the `file_name_matcher` argument, which is a function that returns
    either True or False to indicate a match.
    """

    class FileOrdering(Enum):
        """
        Enumeration of the possible orderings of the files found.
         - HIGHEST_FIRST => files closer to the root directory are first in the list.
         - LOWEST_FIRST => files lowest in the directory tree are first in the list.
        """
        HIGHEST_FIRST = "highest_first"
        LOWEST_FIRST = "lowest_first"
    
    def __init__(self, root_dir: str|Path, sub_dir: str|Path, file_name_matcher: Callable[..., bool]):
        """
        Ctor args:
            start_dir: The directory to start searching in.
            end_dir: The directory to stop searching in.
            file_name_matcher:  a lambda that that returns True to indicate a match, taking either
                one or three arguments like so:
                    - f(file_name:str)
                    - f(dir_path:Path, entries:list[str], file_name:str)
                where:
                    - file_name is the name of the file
                    - dir_path is the path to the directory containing the file
                    - entries is a list of the entries in the directory
        
        Returns:
            Nothing.  Call get_matching_files() to return the list of matching files found.
        """
        self.root_dir:Path = (Path(os.path.expanduser(root_dir)) if isinstance(root_dir, str) else root_dir).resolve()
        self.sub_dir:Path = (Path(os.path.expanduser(sub_dir)) if isinstance(sub_dir, str) else sub_dir).resolve()
        self.file_name_matcher = file_name_matcher
        
        # sanity check input -> ValueError if not valid
        self._ensure_sub_dir_within_root(self.root_dir, self.sub_dir)

        # internally, we store matching files LOWEST_FIRST as strings relative to original sub_dir
        self.matching_files:list[str] = self._walk_up_dir_tree_returning_matches()

    def _ensure_sub_dir_within_root(self, root_dir: Path, sub_dir: Path) -> None:
        """
        Raise ValueError if `sub_dir` is not the same as, or beneath, `root_dir`.
        Both inputs may be relative or absolute; they are resolved before comparison.
        """
        if not sub_dir.is_dir():
            raise ValueError(f"Sub directory {sub_dir} is not a directory")
        if not root_dir.is_dir():
            raise ValueError(f"Root directory {root_dir} is not a directory")
        try:
            sub_dir.relative_to(root_dir)
        except ValueError:
            raise ValueError(f"Sub directory {sub_dir} is not beneath root directory {root_dir}")
        return

    def _walk_up_dir_tree_returning_matches(self) -> list[str]:
        """
        Walk from `self.sub_dir` upward toward `self.root_dir` (inclusive), and
        collect entries in each directory whose names satisfy `self.file_name_matcher`.
        
        Each returned element is a path string relative to the original
        `self.sub_dir` (e.g., '../../c' when a match is located at '/a/b/c' and
        `self.root_dir` == '/a/b/c/d/e'). 
        
        The returned list is in LOWEST_FIRST order (starting at `self.sub_dir` 
        and moving up one parent at a time).
        """
        matching_files:list[str] = []
        root_path = Path(self.root_dir).resolve()
        cur_path = Path(self.sub_dir).resolve()
        while True:
            try:
                entries = os.listdir(cur_path)
            except FileNotFoundError:
                entries = []
            for entry in entries:
                # Support flexible matcher signatures:
                #  - f(name)
                #  - f(dir_path, entries, name)
                try:
                    sig = inspect.signature(self.file_name_matcher)
                    if len(sig.parameters) == 1:
                        match = self.file_name_matcher(entry)
                    else:
                        match = self.file_name_matcher(cur_path, entries, entry)
                except Exception:
                    # Fallback to legacy behavior
                    match = self.file_name_matcher(entry)
                if match:
                    abs_match_path = cur_path / entry
                    rel_to_sub = os.path.relpath(str(abs_match_path), start=str(self.sub_dir))
                    matching_files.append(rel_to_sub)
            if cur_path == root_path:
                break
            cur_path = cur_path.parent
        return matching_files

    def get_matching_files(self, ordering: 'DirWalker.FileOrdering'=FileOrdering.HIGHEST_FIRST) -> list[str]:
        """
        Returns the list of matching files in the order specified by `ordering`.
        
        Args:
            ordering: the ordering of the files to return

        Returns:
            A list[str] of matching file paths.
        """
        if ordering == DirWalker.FileOrdering.HIGHEST_FIRST:
            return list(reversed(self.matching_files))
        elif ordering == DirWalker.FileOrdering.LOWEST_FIRST:
            return list(self.matching_files)
        else:
            raise ValueError(f"Invalid ordering: {ordering}")
