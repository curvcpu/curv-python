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

```shell
$ make show-pypi-versions
```
