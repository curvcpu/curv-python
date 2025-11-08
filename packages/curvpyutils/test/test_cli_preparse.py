import pytest
from click.core import ParameterSource
from curvpyutils.cli_util import EarlyArg, preparse

pytestmark = [pytest.mark.unit]

@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("CURV_ROOT_DIR111", "path/from/env")
    monkeypatch.setenv("CURV_CONFIG111", "path/also/from/env")

@pytest.fixture
def early_args():
    return [
        EarlyArg(["--curv-root-dir111", "-C"], env_var_fallback="CURV_ROOT_DIR111"),
        EarlyArg(["--curv-config111", "-c"], env_var_fallback="CURV_CONFIG111"),
        EarlyArg(["--no-env-var-set", "-n"]),
        EarlyArg(["--has-default-set-only", "-d"], default_value_fallback="default/from/cli"),
    ]

def test_preparse_cli_overrides_root_dir(early_args):
    early_curv_root_dir, early_curv_config, no_env_var_set, has_default_set_only = early_args
    preparse(early_args, argv=["prog", "--curv-root-dir111", "/path/from/cli"])
    assert early_curv_root_dir.value == "/path/from/cli"
    assert early_curv_root_dir.source == ParameterSource.COMMANDLINE
    assert early_curv_config.value == "path/also/from/env"
    assert early_curv_config.source == ParameterSource.ENVIRONMENT
    assert no_env_var_set.value is None
    assert no_env_var_set.source is None
    assert has_default_set_only.value == "default/from/cli"
    assert has_default_set_only.source == ParameterSource.DEFAULT

def test_preparse_cli_overrides_config(early_args):
    early_curv_root_dir, early_curv_config, no_env_var_set, has_default_set_only = early_args
    preparse(early_args, argv=["prog", "--curv-config111", "config/from/cli"])
    assert early_curv_config.value == "config/from/cli"
    assert early_curv_config.source == ParameterSource.COMMANDLINE
    assert no_env_var_set.value is None
    assert no_env_var_set.source is None
    assert has_default_set_only.value == "default/from/cli"
    assert has_default_set_only.source == ParameterSource.DEFAULT

def test_preparse_cli_and_env_interactions(early_args):
    early_curv_root_dir, early_curv_config, no_env_var_set, has_default_set_only = early_args
    preparse(early_args, argv=["prog", "--no-env-var-set", "value/from/cli", "--has-default-set-only", "xyz"])
    assert no_env_var_set.value == "value/from/cli"
    assert no_env_var_set.source == ParameterSource.COMMANDLINE
    assert has_default_set_only.value == "xyz"
    assert has_default_set_only.source == ParameterSource.COMMANDLINE
    assert early_curv_root_dir.value == "path/from/env"
    assert early_curv_root_dir.source == ParameterSource.ENVIRONMENT
    assert early_curv_config.value == "path/also/from/env"
    assert early_curv_config.source == ParameterSource.ENVIRONMENT


