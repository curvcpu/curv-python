# `curv-python` Development

To tweak the code and contribute to `curv-python`, you'll want to follow the steps below to install the packages in editable mode on your local machine.  This enables you to use the tools, but you can also edit the code and open PRs.

## Editable Installation

 1. You need Python 3.10 or higher.

 2. Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/).

 3. Install `slang`, `verilator`, `delta` and `taplo` so they are in your `PATH`. See the CurvCPU [installs.md](https://github.com/curvcpu/curv/blob/main/docs/installs.md) for help.

 4. Clone this repo and set up the developer environment (packages installed editable and CLIs on PATH):

    ```shell
    git clone https://github.com/curvcpu/curv-python.git
    cd curv-python
    make setup
    ```

    This also installs the CLI tools (`curvcfg`, `curv-memmap2`, etc.) into your shell via `uv`.

    If `curvcfg` is not immediately available in your PATH, try closing and reopening your terminal window to see the changes. The PATH change made by `make setup` persists for new shells.

5.  Make sure to append the following line to your `~/.bashrc`, `~/.zprofile`, or similar shell init file to make the editable install work correctly:

    ```shell
    echo 'eval "$(curvtools shellenv)"' >> ~/.bashrc
    ```

    Then restart your shell.

5. To undo the effects of `make setup`, you can run `make unsetup` to remove the editable installs and CLI tools from your shell. (`make setup` has no other system-wide effects.)

## Dev/Test Cycle

- Make changes to the code in the package directories.

- Run tests:

    ```shell
    # from the repo root
    $ make test
    ```

# Publishing to PyPI

Publishing is done from the `main` branch.  You typically run `make publish` for each package individually that you want to publish, or `make publish PKG=all` to publish all packages at once.

⚠️ **Be careful about dependencies:**

- `curvtools` depends on `curv` which depends on `curvpyutils`
- `curv` depends on `curvpyutils`

Thus, to upgrade `curvtools` you may also need to publish the latest versions of `curv` and `curvpyutils` at the same time if they have changed and `curvtools` depends on the latest versions of them.

## Detailed Steps for Publishing

1. Build and make sure tests pass:

    ```shell
    $ make build
    $ make test
    ```

2.  Run this tool to see which dependent packages need to be republished.

For example, if you want to publish `curvtools`:

    ```shell
    $ make publish-advice PKG=curvtools
    ```

Output will look something like this:

    ```shell
    $ make publish-advice PKG=curvtools

                        If you want to publish curvtools...                        
    ┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
    ┃ Package     ┃ Latest Commit Time     ┃ Latest Tag Time        ┃ Needs Publish? ┃
    ┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
    │ curvpyutils │ 2025-11-13 11:18:35am  │ 2025-11-12 09:18:18am  │ ⚠️ Yes         │
    │ curvtools   │ 2025-11-12 10:13:05am  │ 2025-11-12 10:18:07am  │ 🚫 No          │
    └─────────────┴────────────────────────┴────────────────────────┴────────────────┘

    ╭──────── Recommended make command for publishing `curvtools` ─────────╮
    │                                                                      │
    │  make publish PKG="curvpyutils curvtools" LEVEL=<patch|minor|major>  │
    │                                                                      │
    ╰──────────────────────────────────────────────────────────────────────╯
    ```

3. Publish the package(s) by running the recommended `make` command from Step 2

Example:

    ```shell
    $ make publish PKG="curvpyutils curvtools" LEVEL=patch
    ```

4.  Watch the CI status of the publish:

    ```shell
    $ make show-publish-status
    ```

    or, just browse to [https://github.com/curvcpu/curv-python/actions](https://github.com/curvcpu/curv-python/actions) to see the CI status of the publish.

5.  If the publish fails, you can undo the tag by deleting it locally and pushing the tag deletion to the remote repository:

    ```shell
    $ make untag PKG=PKG VER=X.Y.Z
    ```

    Example: delete the failed publish tag for `curv` version `0.0.6` from both the local tags and remote tags:

    ```shell
    $ make untag PKG=curv VER=0.0.6
    ```

    This is equivalent to manually running these commands:

    ```shell
    $ git tag -d PKG-vX.Y.Z
    $ git push --delete origin PKG-vX.Y.Z
    ```

6. If you're not sure what versions failed and should be untagged...

    This command will show the latest PyPI published version for each package and its local tags:

    ```shell
    $ make show
    ```

## Helpful Git Aliases

This is not particularly unique to this repo, but some git aliases I have found helpful are documented in [docs/git-aliases.md](../docs/git-aliases.md).
