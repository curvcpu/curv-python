# `curvtools` package

CLI tools for the Curv RISC-V CPU project.

## Prerequisites

- Follow the [developer setup instructions](../.github/CONTRIBUTING.md#editable-installation) including installing `uv` and running `make setup` (only needed once per machine).

## Development/testing of CLI tools

We'll use the `memmap2` tool as an example.  Here are some common tasks:

- Run one of the CLI tools (they're in your `PATH` after `make setup`):

    ```shell
    curv-memmap2 --help
    ```

- Run tests just for one tool using `pytest` from its source directory:

    ```shell
    # from the repo root
    $ cd packages/curvtools/src/curvtools/cli/memmap2
    $ pytest
    ```
