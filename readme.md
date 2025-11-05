# curv-python

This is a monorepo for the Curv Python packages, `curv` and `curvtools` and the shared utilities package, `curvpyutils` on which they both depend.

## Development/testing

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

## Publishing

### Publish a package

Publishing packages is done manually, so be careful about dependencies:  They all depend on `curvpyutils`, and `curvtools` depends on `curv` as well as `curvpyutils`.

- `curvtools` depends on `curv` which depends on `curvpyutils`
- `curv` depends on `curvpyutils`

Publishing a package automatically bumps the version based on the `LEVEL` argument:

```shell
$ make publish PKG=curv LEVEL=patch
$ make publish PKG=curvtools LEVEL=patch
$ make publish PKG=curvpyutils LEVEL=patch
```

### What is published on PyPI right now?

This will show the latest published version for each package and its local tags.

```shell
$ make show
```

### Undo a tag (git tag) if the publish failed

You can delete any tag (both local and remote) if it's newer than some version number for a given package.

```shell
# delete failed publish tags by deleting any tag newer than VER for PKG=curvtools
$ make untag PKG=curvtools VER=0.0.6
```

```shell
# Clean up any tags newer than what's published
make untag PKG=curvpyutils  
```

You must specify a package name:

```shell
# Error case - PKG always required on command line
make untag  # → Error: PKG= must be specified
```

And you cannot delete tags older than the latest published version on PyPI:

```shell
# ❌ ERROR: Cannot delete tags older than published version
$ make untag PKG=curvtools VER=0.0.1
# Output: "Error: Cannot delete tags older than or equal to published version 0.0.6"
```