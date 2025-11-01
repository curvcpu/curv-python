import os


def find_path_by_leaf(root_dir: str, leaf_path: str) -> str | None:
    """Search for a path ending with ``leaf_path`` inside ``root_dir``.

    Args:
        root_dir: Directory to start the traversal from.
        leaf_path: The partial terminal path to locate.

    Returns:
        Absolute path to the located leaf, or ``None`` if not found.
    """

    if not root_dir or not leaf_path:
        return None

    if os.path.isabs(leaf_path) and os.path.exists(leaf_path):
        return os.path.abspath(leaf_path)

    rel_leaf = leaf_path.lstrip(os.sep)

    direct_candidate = os.path.join(root_dir, rel_leaf)
    if os.path.exists(direct_candidate):
        return os.path.abspath(direct_candidate)

    for dirpath, _dirnames, _filenames in os.walk(root_dir, topdown=True):
        candidate = os.path.join(dirpath, rel_leaf)
        if os.path.exists(candidate):
            return os.path.abspath(candidate)

    return None

