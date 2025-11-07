# `curv-python` Development

To tweak the code and contribute to `curv-python`, you'll want to follow the steps below to install the packages in editable mode on your local machine.  This enables you to use the tools, but you can also edit the code and open PRs.

## Editable Installation

 1. You need Python 3.10 or higher.

 2. Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/).

 3. Install `slang`, `verilator` and `delta` so they are in your `PATH`. See the CurvCPU [installs.md](https://github.com/curvcpu/curv/blob/main/docs/installs.md) for help.

 4. Clone this repo and set up the developer environment (packages installed editable and CLIs on PATH):

    ```shell
    git clone https://github.com/curvcpu/curv-python.git
    cd curv-python
    make setup
    ```

    This also installs the CLI tools (`curv-cfg`, `curv-memmap2`, etc.) into your shell via `uv`.

    If `curvcfg` is not immediately available in your PATH, try closing and reopening your terminal window to see the changes. The PATH change made by `make setup` persists for new shells.

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

2.  Push a commit to the main branch to see if tests pass in CI.

    ```shell
    # change something in a file...
    $ git add .
    $ git commit -m "whatever"
    $ git push
    ```

3. Bump version and publish:

    `make publish` automatically bumps the version based on the `LEVEL` argument you provide (meaning whether to bump the major, minor, or patch version).

    ```shell
    $ make publish PKG=curv LEVEL=patch
    $ make publish PKG=curvtools LEVEL=patch
    $ make publish PKG=curvpyutils LEVEL=patch
    ```

4.  Watch the CI status of the publish:

    ```shell
    $ make show-publish-status
    ```

    or, obviously, just browse to [https://github.com/curvcpu/curv-python/actions](https://github.com/curvcpu/curv-python/actions).

5.  If the publish fails, you can undo the tag by deleting it locally and pushing the delete:

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

### Undo a Tag (`git tag`) When the Publish Failed

 - You can delete any tag (both local and remote) if it's newer than some version number for a given package.

    ```shell
    # delete failed publish tags by deleting any tag newer than VER for PKG=curvtools
    $ make untag PKG=curvtools VER=0.0.6
    ```

 - Or a simple alternative to clean up all local/remote tags that failed to publish:

    ```shell
    # Clean up any tags newer than what's published
    make untag PKG=curvpyutils
    ```

 - Safety features of the `make untag` command:

    ```shell
    # You must specify a package name:
    make untag  # → Error: PKG= must be specified
    ```

    ```shell
    # ❌ ERROR: Cannot delete tags older than published version
    $ make untag PKG=curvtools VER=0.0.1
    # Output: "Error: Cannot delete tags older than or equal to published version 0.0.6"
    ```
