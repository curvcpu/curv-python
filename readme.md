# curv-python

<!-- Release (latest tag) -->
[![release](https://img.shields.io/github/v/tag/curvcpu/curv-python?label=release)](https://github.com/curvcpu/curv-python/releases)

<!-- Version (static example) -->
[![version](https://img.shields.io/badge/v2.1.1-blue)](https://github.com/OWNER/REPO/releases/tag/v2.1.1)

<!-- Build (GitHub Actions workflow) -->
[![build](https://github.com/curvcpu/curv-python/actions/workflows/ci.yaml/badge.svg?branch=main)](https://github.com/curvcpu/curv-python/actions/workflows/ci.yaml)

[![license](https://img.shields.io/github/license/curvcpu/curv-python)](LICENSE)
[![issues](https://img.shields.io/github/issues/curvcpu/curv-python)](https://github.com/curvcpu/curv-python/issues)
[![last commit](https://img.shields.io/github/last-commit/curvcpu/curv-python)](https://github.com/curvcpu/curv-python/commits)

This is a monorepo for the Curv Python packages, `curv` and `curvtools` and the shared utilities package, `curvpyutils` on which they both depend.

# Installation

The recommended installation method is to use [`pipx`](https://pipx.pypa.io/latest/installation/) to install  `curvtools` CLI tools.  You don't need to clone this repo.

  - **macOS:**

    ```shell
     brew install pipx
     pipx ensurepath
     pipx install curvtools
     ```

  - **Ubuntu 22.04 LTS and later:**

     ```shell
     sudo apt install pipx
     pipx install curvtools
     ```

  - **Windows and other Linux distributions:** see [pipx installation instructions](https://pipx.pypa.io/latest/installation/).

# Usage

Once installed with `pipx`, all the command line tools needed to build the Curv CPU will be in your `PATH`:

```shell
curv-cfg --help
curv-cache-tool --help
curv-subst --help
curv-memmap2 --help
curv-clog2 --help
```

These tools are called automatically by the build process for the [Curv CPU](https://github.com/curvcpu/curv).  To simply get the CPU working, you really don't need to know anything about them.  Just make sure they are in your `PATH` and you're good to go.

# Contributing to `curv-python`

If you want to tweak the code or contribute to the project, skip the `pipx` install described above and instead follow the steps in the [contributing guide](.github/CONTRIBUTING.md).