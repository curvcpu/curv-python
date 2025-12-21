# `curvpyutils`

Utility functions used by the Curv Python packages, `curv` and `curvtools`.

## Development/testing

- cd into the package directory:

```shell
cd packages/curvpyutils
```

- Create venv + install packages in editable mode
- Run both unit and e2e tests:

```shell
pytest -m "unit or e2e"
```

## Demo

- `multi_progress` has a demo script that can be run to see the progress bars in action:

```shell
cd test
python multi_progress_demos.py
```

## TOML helper functions

- `curvpyutils.tomlrw` provides helper functions for working with TOML files across multiple Python versions:

    ```python
    import curvpyutils.tomlrw as tomlrw

    d = {"a": 1, "b": 2}
    s = tomlrw.dumps(d)
    print(s)
    ```

- Other functions include `loadf` and `loads` for reading TOML files and strings into dictionaries.  See [test_tomlrw.py](test/test_tomlrw.py) for examples.









