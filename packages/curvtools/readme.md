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

## `curvcfg`

`curvcfg` is a command line tool for managing the configuration of the Curv CPU.  It is used to merge and generate configuration files for the CPU.

Here is a quick rundown of how to use it (paths below are representative—set `CURV_ROOT_DIR` per the [curvcpu/curv](https://github.com/curvcpu/curv) docs and point `CURV_BUILD_DIR` at a scratch build dir like `./build`):

- Board flow: merge board config, then generate HDL/make artifacts

    ```shell
    CURV_BUILD_DIR=build curvcfg [-vv] board merge \
      --board=ulx3s --device=85f \
      --schema=$CURV_ROOT_DIR/boards/schema/schema.toml \
      --schema=$CURV_ROOT_DIR/boards/schema/schema_flash.toml
[
    CURV_BUILD_DIR=build curvcfg [-vv] board generate \
      --merged-board-toml build/generated/config/merged_board.toml \
      --template=$CURV_ROOT_DIR/boards/templates/boardpkg.sv.jinja2
    ```

    Representative outputs: `generated/config/merged_board.toml`, `generated/make/board.mk(.d)`, `generated/hdl/boardpkg.sv`, `generated/hdl/board.svh`, `generated/shell/board.env`.

- Configuration variables flow: `merge cfgvars`, then generate remaining artifacts

    ```shell
    CURV_BUILD_DIR=build curvcfg [-vv] cfgvars merge \
      --profile=default \
      --schema=$CURV_ROOT_DIR/config/schema/schema.toml \
      --schema=$CURV_ROOT_DIR/config/schema/tb-extras-schema.toml \
      --overlay=$CURV_ROOT_DIR/config/profiles/overlays/tb.toml

    CURV_BUILD_DIR=build curvcfg [-vv] cfgvars generate \
      --merged-config-toml build/generated/config/merged_cfgvars.toml
    ```

    Representative outputs: `generated/config/merged_cfgvars.toml`, `generated/make/config.mk.d` + `curv.mk`, `generated/hdl/curvcfgpkg.sv`, `generated/hdl/curvcfg.svh`, `generated/shell/curv.env`.

- Show derived paths from `scripts/make/paths_raw.env` in the [curvcpu/curv](https://github.com/curvcpu/curv) repo

    ```shell
    CURV_BUILD_DIR=build curvcfg [-vv] show curvpaths \
      --board=ulx3s --device=85f --profile=default
    ```

- Inspect merged variables for any merged `*.toml`

    ```shell
    CURV_BUILD_DIR=build curvcfg [-vv] show vars \
      --merged-toml=build/generated/config/merged_board.toml

    CURV_BUILD_DIR=build curvcfg [-vv] show vars \
      --merged-toml=build/generated/config/merged_cfgvars.toml
    ```

