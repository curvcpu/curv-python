# curv-python

<p align="center">
  <!-- @subst[`printf '<a href="https://github.com/curvcpu/curv-python/releases/tag/curv-v$CURV_VER_MAJMINPTCH"><img src="https://img.shields.io/badge/v$CURV_VER_MAJMINPTCH-blue?label=curv" alt="curv version $CURV_VER_MAJMINPTCH"></a>\n'`] -->
  <a href="https://github.com/curvcpu/curv-python/releases/tag/curv-v0.1.14"><img src="https://img.shields.io/badge/v0.1.14-blue?label=curv" alt="curv version 0.1.14"></a>
  <!-- @endsubst -->
  <!-- @subst[`printf '<a href="https://github.com/curvcpu/curv-python/releases/tag/curvtools-v$CURVTOOLS_VER_MAJMINPTCH"><img src="https://img.shields.io/badge/v$CURVTOOLS_VER_MAJMINPTCH-blue?label=curvtools" alt="curvtools version $CURVTOOLS_VER_MAJMINPTCH"></a>\n'`] -->
  <a href="https://github.com/curvcpu/curv-python/releases/tag/curvtools-v0.0.12"><img src="https://img.shields.io/badge/v0.0.12-blue?label=curvtools" alt="curvtools version 0.0.12"></a>
  <!-- @endsubst -->
  <!-- @subst[`printf '<a href="https://github.com/curvcpu/curv-python/releases/tag/curvpyutils-v$CURVPYUTILS_VER_MAJMINPTCH"><img src="https://img.shields.io/badge/v$CURVPYUTILS_VER_MAJMINPTCH-blue?label=curvpyutils" alt="curvpyutils version $CURVPYUTILS_VER_MAJMINPTCH"></a>\n'`] -->
  <a href="https://github.com/curvcpu/curv-python/releases/tag/curvpyutils-v0.0.44"><img src="https://img.shields.io/badge/v0.0.44-blue?label=curvpyutils" alt="curvpyutils version 0.0.44"></a>
  <!-- @endsubst -->
</p>

<p align="center">
  <!-- <a href="https://github.com/curvcpu/curv-python/releases"><img src="https://img.shields.io/github/v/tag/curvcpu/curv-python?label=release" alt="Latest Release"></a> -->
  <a href="https://github.com/curvcpu/curv-python/actions/workflows/ci.yaml"><img src="https://github.com/curvcpu/curv-python/actions/workflows/ci.yaml/badge.svg?branch=main" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/curvcpu/curv-python" alt="LICENSE"></a>
  <a href="https://github.com/curvcpu/curv-python/commits"><img src="https://img.shields.io/github/last-commit/curvcpu/curv-python" alt="Last Commit"></a>
  <!-- <a href="https://github.com/pre-commit/pre-commit"><img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit" alt="pre-commit" style="max-width:100%;"></a> -->
</p>

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
```

These tools are called automatically by the build process for the [Curv CPU](https://github.com/curvcpu/curv).  To simply get the CPU working, you really don't need to know anything about them.  Just make sure they are in your `PATH` and you're good to go.

# Contributing to `curv-python`

If you want to tweak the code or contribute to the project, skip the `pipx` install described above and instead follow the steps in the [contributing guide](.github/CONTRIBUTING.md).