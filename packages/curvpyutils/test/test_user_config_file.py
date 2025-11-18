import os
from pathlib import Path

import pytest

from curvpyutils.system.user_config_file import UserConfigFile


@pytest.fixture
def cfg(tmp_path, monkeypatch) -> UserConfigFile:
    """
    Use a temp XDG_CONFIG_HOME so we don't touch the real user config.
    This assumes a POSIX-ish platform where platformdirs respects XDG_CONFIG_HOME.
    """
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg = UserConfigFile(app_name="curv")  # config path: $XDG_CONFIG_HOME/curv/config.toml
    # Make sure we start clean
    if cfg.config_file_path.exists():
        cfg.delete()
    return cfg


def test_read_kv_returns_nested_value(cfg: UserConfigFile):
    cfg.write(
        {
            "curvtools": {
                "CURV_PYTHON_EDITABLE_REPO_PATH": "/home/mwg/curv-python",
                "int_value": 123,
            }
        }
    )

    assert (
        cfg.read_kv("curvtools.CURV_PYTHON_EDITABLE_REPO_PATH")
        == "/home/mwg/curv-python"
    )
    assert cfg.read_kv("curvtools.int_value") == 123


def test_read_kv_returns_default_for_missing_key(cfg: UserConfigFile):
    cfg.write({"curvtools": {}})

    assert cfg.read_kv("curvtools.missing", default="fallback") == "fallback"
    # different branch: first segment missing
    assert cfg.read_kv("does_not_exist.at_all", default=42) == 42


def test_read_kv_raises_keyerror_when_missing_and_no_default(cfg: UserConfigFile):
    cfg.write({"curvtools": {}})

    with pytest.raises(KeyError):
        cfg.read_kv("curvtools.missing")

    with pytest.raises(KeyError):
        cfg.read_kv("totally.missing.path")


def test_read_kv_non_dict_intermediate_treated_as_missing(cfg: UserConfigFile):
    # curvtools is a scalar, not a dict
    cfg.write({"curvtools": 123})

    # no default -> KeyError
    with pytest.raises(KeyError):
        cfg.read_kv("curvtools.foo")

    # with default -> default returned
    assert cfg.read_kv("curvtools.foo", default="fallback") == "fallback"


def test_upsert_kv_creates_nested_structures(cfg: UserConfigFile):
    cfg.write({})  # start from empty file

    cfg.upsert_kv("curvtools.CURV_PYTHON_EDITABLE_REPO_PATH", "/tmp/curv-python")

    full = cfg.read()
    assert full == {
        "curvtools": {
            "CURV_PYTHON_EDITABLE_REPO_PATH": "/tmp/curv-python",
        }
    }

    # sanity: read_kv sees the value
    assert (
        cfg.read_kv("curvtools.CURV_PYTHON_EDITABLE_REPO_PATH")
        == "/tmp/curv-python"
    )


def test_upsert_kv_overwrites_leaf_value(cfg: UserConfigFile):
    cfg.write(
        {
            "curvtools": {
                "CURV_PYTHON_EDITABLE_REPO_PATH": "/old/path",
            }
        }
    )

    cfg.upsert_kv("curvtools.CURV_PYTHON_EDITABLE_REPO_PATH", "/new/path")

    full = cfg.read()
    assert full["curvtools"]["CURV_PYTHON_EDITABLE_REPO_PATH"] == "/new/path"


def test_upsert_kv_preserves_unrelated_keys(cfg: UserConfigFile):
    cfg.write(
        {
            "curvtools": {
                "existing_key": 1,
            },
            "other_section": {
                "other_key": 2,
            },
        }
    )

    cfg.upsert_kv("curvtools.new_key", "value")

    full = cfg.read()
    assert full["curvtools"]["existing_key"] == 1
    assert full["curvtools"]["new_key"] == "value"
    assert full["other_section"]["other_key"] == 2


def test_upsert_kv_creates_deeply_nested_path(cfg: UserConfigFile):
    cfg.write({})

    cfg.upsert_kv("a.b.c.d", 123)

    full = cfg.read()
    assert full == {"a": {"b": {"c": {"d": 123}}}}
    assert cfg.read_kv("a.b.c.d") == 123


def test_upsert_kv_overwrites_when_intermediate_is_not_dict(cfg: UserConfigFile):
    cfg.write({"a": {"b": 1}})
    
    cfg.upsert_kv("a.b.c", 42)
    
    assert cfg.read() == {"a": {"b": {"c": 42}}}