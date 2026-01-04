# curv-python

<p align="center">
  <!-- @subst[`printf '<a href="https://github.com/curvcpu/curv-python/releases/tag/curv-v$CURV_VER_MAJMINPTCH"><img src="https://img.shields.io/badge/v$CURV_VER_MAJMINPTCH-blue?label=curv" alt="curv version $CURV_VER_MAJMINPTCH"></a>\n'`] -->
  <a href="https://github.com/curvcpu/curv-python/releases/tag/curv-v0.1.14"><img src="https://img.shields.io/badge/v0.1.14-blue?label=curv" alt="curv version 0.1.14"></a>
  <!-- @endsubst -->
  <!-- @subst[`printf '<a href="https://github.com/curvcpu/curv-python/releases/tag/curvtools-v$CURVTOOLS_VER_MAJMINPTCH"><img src="https://img.shields.io/badge/v$CURVTOOLS_VER_MAJMINPTCH-blue?label=curvtools" alt="curvtools version $CURVTOOLS_VER_MAJMINPTCH"></a>\n'`] -->
  <a href="https://github.com/curvcpu/curv-python/releases/tag/curvtools-v0.0.19"><img src="https://img.shields.io/badge/v0.0.19-blue?label=curvtools" alt="curvtools version 0.0.19"></a>
  <!-- @endsubst -->
  <!-- @subst[`printf '<a href="https://github.com/curvcpu/curv-python/releases/tag/curvpyutils-v$CURVPYUTILS_VER_MAJMINPTCH"><img src="https://img.shields.io/badge/v$CURVPYUTILS_VER_MAJMINPTCH-blue?label=curvpyutils" alt="curvpyutils version $CURVPYUTILS_VER_MAJMINPTCH"></a>\n'`] -->
  <a href="https://github.com/curvcpu/curv-python/releases/tag/curvpyutils-v0.0.51"><img src="https://img.shields.io/badge/v0.0.51-blue?label=curvpyutils" alt="curvpyutils version 0.0.51"></a>
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

# Prerequisites

- Python 3.10 or higher
- `uv`
- `slang`, `verilator`, `delta` and `taplo`

Below are instructions for [macOS 👇](#on-macos) and [Ubuntu 22.04 LTS+ 👇](#on-ubuntu-2204-lts-and-later).

### On macOS

```shell
# --- install Homebrew if you don't have it ---
/bin/bash -c \
"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# --- verilator + delta + taplo + build/tooling equivalents ---
brew update
brew install verilator git-delta git curl wget gnu-tar coreutils taplo

# --- uv ---
curl -LsSf https://astral.sh/uv/install.sh | sh
# make sure uv is on PATH (installer typically updates shell rc)
# pick ONE based on your shell:
source ~/.zshrc 2>/dev/null || true
source ~/.bashrc 2>/dev/null || true
uv --version # verify installation

# --- slang ---
# pick the correct asset for your CPU:
# Apple Silicon (arm64):
wget -O slang-macos.tar.gz \
https://github.com/MikePopoloski/slang/releases/latest/download/slang-macos-arm64.tar.gz
# Intel (x86_64):
# wget -O slang-macos.tar.gz \
#   https://github.com/MikePopoloski/slang/releases/latest/download/slang-macos-x86_64.tar.gz
tar -xzf slang-macos.tar.gz
# install somewhere sensible; macOS doesn't use /opt the same way Linux does, but it works.
# /usr/local is typical on Intel; /opt/homebrew is typical on Apple Silicon.
sudo mkdir -p /opt/slang
sudo mv slang /opt/slang
# symlink slang into PATH (Apple Silicon; adapt for x86_64 Intel)
sudo ln -sf /opt/slang/bin/slang /opt/homebrew/bin/slang
slang --version # verify installation
```

### On Ubuntu 22.04 LTS and later

```shell
# --- verilator + delta + prereqs used later ---
sudo apt update
sudo apt install -y verilator git-delta build-essential procps curl file git

# --- uv ---
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc && uv --version # verify installation

# --- taplo ---
# (assumes linuxbrew; install with `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
# or see the linuxbrew docs at https://docs.brew.sh/Installation)
brew install taplo

# --- slang prebuilt binary ---
wget -O slang-linux-x86_64.tar.gz \
https://github.com/MikePopoloski/slang/releases/latest/download/slang-linux-x86_64.tar.gz
tar -xzf slang-linux-x86_64.tar.gz
sudo mv slang /opt/slang
sudo ln -s /opt/slang/bin/slang /usr/local/bin/slang
```

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
curv-cfg --help # or curvcfg --help
curv-cache-tool --help
curv-cache-tool-tag-ram-way-interleaver --help
curv-subst --help
curv-memmap2 --help
curv-verilog-hex-generate --help
curv-verilog-hex-reformat --help
```

These tools are called automatically by the build process for the [Curv CPU](https://github.com/curvcpu/curv).  To simply get the CPU working, you really don't need to know anything about them.  Just make sure they are in your `PATH` and you're good to go.

Additional information on `curvcfg` is available in the [curvcfg README](packages/curvtools/readme.md#curvcfg).

# Contributing to `curv-python`

If you want to tweak the code or contribute to the project, skip the `pipx` install described above and instead follow the steps in the [contributing guide](.github/CONTRIBUTING.md).