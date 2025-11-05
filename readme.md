# curv-python

This is a monorepo for the Curv Python packages, `curv` and `curvtools` and the shared utilities package, `curvpyutils` on which they both depend.

# Development/testing

- Create venv + install packages in editable mode:

```shell
make install-dev
```

- Run tests:

```shell
make test        # run both unit and CLI e2e tests
make test-unit   # just the unit tests
make test-e2e    # just the CLI e2e tests (exercises installed CLIs)
```

# Publishing to PyPI

Publishing the three packages is done manually one at a time.

Be careful about dependencies:

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

4.  If the publish failes, you can undo the tag by deleting it locally and pushing the delete:

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

5. If you're not sure what versions failed to publish and should be untagged...

This command will show the latest PyPI published version for each package and its local tags:

```shell
$ make show
```

### Undo a Tag (`git tag`) When the Publish Failed

You can delete any tag (both local and remote) if it's newer than some version number for a given package.

```shell
# delete failed publish tags by deleting any tag newer than VER for PKG=curvtools
$ make untag PKG=curvtools VER=0.0.6
```

Or a simple alternative to clean up all local/remote tags that failed to publish:

```shell
# Clean up any tags newer than what's published
make untag PKG=curvpyutils
```

Safety features of the `make untag` command:

```shell
# You must specify a package name:
make untag  # → Error: PKG= must be specified
```

```shell
# ❌ ERROR: Cannot delete tags older than published version
$ make untag PKG=curvtools VER=0.0.1
# Output: "Error: Cannot delete tags older than or equal to published version 0.0.6"
```