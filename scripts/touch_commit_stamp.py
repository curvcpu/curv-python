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
    "packages/curv/":        "packages/curv/src/curv/.package_changed_stamp.txt",
    "packages/curvpyutils/": "packages/curvpyutils/src/curvpyutils/.package_changed_stamp.txt",
    "packages/curvtools/":   "packages/curvtools/src/curvtools/.package_changed_stamp.txt",
}

# don't re-touch stamps if the only thing that changed was the stamp itself
EXCLUDED_FILES = [stamp for stamp in PKGS.values()]

def list_changed_in_head() -> list[str]:
    # robust for initial commits, merges, etc.
    out = subprocess.check_output(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
        text=True
    )
    return [p for p in out.splitlines() if p]

def touch(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        os.utime(path, None)          # update mtime only
    except FileNotFoundError:
        try:
            with open(path, "x") as f:
                f.write("# empty file whose mtime is used to track last commit that changed this package\n")
                f.write("\n")
                f.write("# *do* commit this to source control\n")
        except FileNotFoundError:
            raise
    subprocess.run(
        ["git", "add", path],
        check=True
    )

def main(argv):
    # keep track of whether we've already touched the stamps
    touched_stamps = False

    # first time only: create any stamps that don't exist yet
    for pfx, stamp in PKGS.items():
        if not os.path.exists(stamp):
            touch(stamp)
            touched_stamps = True
            print(f"created {stamp} because it didn't exist yet")
    
    # normal operation: touch any stamps that are triggered by changes to files under the given package path
    files: list[str] = argv or list_changed_in_head()      # if run as pre-commit, filenames arrive in argv
    files = [f for f in files if not f in EXCLUDED_FILES]  # exclude files that we don't want to trigger on
    console.print(f"[bold yellow]files:[/bold yellow] {files}")
    console.print(f"[bold yellow]excluded_files:[/bold yellow] {EXCLUDED_FILES}")

    # example of to_touch:
    # {'packages/curv/.package_changed_stamp.txt': 
    #      {'triggered_by': ['packages/curv/src/curv/foo.py', 'packages/curv/src/curv/bar.py']}
    # }
    to_touch = {}
    for pfx, stamp in PKGS.items():
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
            console.print(f"    [bold yellow]● {f}[/bold yellow]")
        console.print("")

    # if touched_stamps:
    #     console.print(f"[bold red]Re-run your `git commit` command and it will work now with updated stamp file(s) added[/bold red]")
    #     sys.exit(1)
    # else:
    sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1:])