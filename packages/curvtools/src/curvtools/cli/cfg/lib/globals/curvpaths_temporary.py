import os

def get_curv_root_dir_from_repo_root(repo_root_dir: str, invert: bool = False) -> str:
    """
    Temporary because soon CURV_ROOT_DIR will be the repo root. For now, we need
    to add "my-designs/riscv-soc" to the repo root.

    If invert is True, it means we are trying to get the repo root from the CURV_ROOT_DIR,
    so we need to reverse the process and join with "../..".
    """
    if invert:
        return os.path.join(repo_root_dir, "../..")
    else:
        return os.path.join(repo_root_dir, "my-designs/riscv-soc")