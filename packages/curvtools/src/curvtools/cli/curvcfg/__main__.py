#! /usr/bin/env python3

import sys

from .cli import main as _main


# never executes; __main__.py is used for testing only
def main() -> None:
    sys.exit(_main())

# never executes; __main__.py is used for testing only
if __name__ == "__main__":
    main()