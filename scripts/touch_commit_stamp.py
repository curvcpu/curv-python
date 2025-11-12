#!/usr/bin/env python3

# /// script
# requires-python = ">=3.10"
# dependencies = ["rich>=13"]
# ///
import os, subprocess, sys
from rich.console import Console
from rich.text import Text

console = Console()

# map dir prefix -> stamp path
PKGS = {
    "packages/curv/":        {
                                "last_changed_stamp_file": "packages/curv/src/curv/.package_changed_stamp.stamp", 
                                "last_published_stamp_file": "packages/curv/src/curv/.package_published_stamp.stamp",
                             },
    "packages/curvpyutils/": {
                                "last_changed_stamp_file": "packages/curvpyutils/src/curvpyutils/.package_changed_stamp.stamp", 
                                "last_published_stamp_file": "packages/curvpyutils/src/curvpyutils/.package_published_stamp.stamp",
                             },
    "packages/curvtools/":   {
                                "last_changed_stamp_file": "packages/curvtools/src/curvtools/.package_changed_stamp.stamp", 
                                "last_published_stamp_file": "packages/curvtools/src/curvtools/.package_published_stamp.stamp",
                              },
}

# don't re-touch stamps if the only thing that changed was the stamp itself
EXCLUDED_FILES = [info["last_changed_stamp_file"] for info in PKGS.values()]

def get_latest_published_ts(pkg:str) -> int:
    # get the latest published version from PyPI
    p = subprocess.run(
        ['python3', 'scripts/chk-latest-version.py', '-L', '-ts', 'epoch', pkg]
    )
    if p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, p.args)
    return int(p.stdout.strip())

def get_latest_tag_ts(pkg:str) -> tuple[str, int]:
    def sh(*args, **kw):
        return subprocess.check_output(args, text=True, **kw).strip()

    # newest by creation date; returns (tag_name, ts)
    tag_glob = f"{pkg}-v*"
    tag = sh('bash','-lc', f"git for-each-ref --sort=-creatordate --format='%(refname:short)' refs/tags/{tag_glob} | head -n1")
    if not tag:
        return None, None
    # taggerdate (annotated) if present, else commit date
    try:
        ts = sh('git','for-each-ref','--format=%(taggerdate:unix)', f'refs/tags/{tag}')
        if not ts:
            ts = sh('git','log','-1','--format=%ct', tag)
    except subprocess.CalledProcessError:
        ts = sh('git','log','-1','--format=%ct', tag)
    return tag, int(ts)

def list_changed_in_head() -> list[str]:
    # robust for initial commits, merges, etc.
    out = subprocess.check_output(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
        text=True
    )
    return [p for p in out.splitlines() if p]

def touch(path: str, mtime_epoch: int|float|None = None) -> None:
    from datetime import datetime, timezone
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "x") as f:
            f.write("# empty file whose mtime is used by make to track whether last commit was more recent than last published time\n")
            f.write("# *do not* commit to source control\n")
    st_atime, st_mtime = os.stat(path)
    if mtime_epoch is None:
        new_mtime: float = st_mtime
    else:
        new_mtime: float = float(mtime_epoch)
    os.utime(path, (st_atime, new_mtime))

def main(argv):
    latest_tag, latest_tag_ts = get_latest_tag_ts(pkg='curv')
    console.print(f"[bold yellow]latest_tag:[/bold yellow] {latest_tag}")
    console.print(f"[bold yellow]latest_tag_ts:[/bold yellow] {latest_tag_ts}")
    sys.exit(0)

    # keep track of whether we've already touched the stamps
    touched_stamps = False

    # first time only: create any stamps that don't exist yet
    for pfx, info in PKGS.items():
        changed_stamp = info["last_changed_stamp_file"]
        published_stamp = info["last_published_stamp_file"]
        if not os.path.exists(changed_stamp):
            touch(changed_stamp)
            touched_changed_stamps = True
            print(f"created {changed_stamp} because it didn't exist yet")
        if not os.path.exists(published_stamp):
            touch(published_stamp)
            touched_published_stamps = True
            print(f"created {published_stamp} because it didn't exist yet")
    
    # normal operation: touch any stamps that are triggered by changes to files under the given package path
    files: list[str] = argv or list_changed_in_head()      # if run as pre-commit, filenames arrive in argv
    files = [f for f in files if not f in EXCLUDED_FILES]  # exclude files that we don't want to trigger touch on
    console.print(f"[bold yellow]files:[/bold yellow] {files}")
    console.print(f"[bold yellow]excluded_files:[/bold yellow] {EXCLUDED_FILES}")

    # example of to_touch:
    # {'packages/curv/.package_changed_stamp.txt': 
    #      {'triggered_by': ['packages/curv/src/curv/foo.py', 'packages/curv/src/curv/bar.py']}
    # }
    to_touch = {}
    for pfx, info in PKGS.items():
        stamp = info["last_changed_stamp_file"]
        for f in files:
            if f.startswith(pfx):
                if to_touch.get(stamp) is None: 
                    to_touch[stamp] = {'triggered_by': []}
                to_touch[stamp]['triggered_by'].append(f)
    
    # touch each stamp and print a summary of the changes that triggered it
    for stamp, data in sorted(to_touch.items()):
        touch(stamp)
        touched_stamps = True
        console.print(f"Touched [bold green]{stamp}[/bold green] because of changes to these files:")
        for f in data['triggered_by']:
            console.print(f"    [bold yellow]• {f}[/bold yellow]")
        console.print("")

    sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1:])