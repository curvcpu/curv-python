# curv-python

## Dev/test loop

### create venv + install packages in editable mode
make install-dev

### run tests
make test-unit
make test-e2e    # exercises installed CLIs

## Publishing

### show PyPI versions if you're curious
make show-pypi-versions

### publish a package

Publishing packages is done manually, so be careful about dependencies.  They all depend on `curvpyutils`, and `curvtools` depends on `curv` as well as `curvpyutils`.

```shell
$ make publish PKG=curv LEVEL=minor
$ make publish PKG=curvtools LEVEL=minor
$ make publish PKG=curvpyutils LEVEL=minor
```
