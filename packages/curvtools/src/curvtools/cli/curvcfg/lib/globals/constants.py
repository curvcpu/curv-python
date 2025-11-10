PROGRAM_NAME = "curvcfg"
PACKAGE_NAME = "curvtools"

# output files from merge command
DEFAULT_MERGED_TOML_NAME = "merged.toml"
DEFAULT_DEP_FILE_NAME = "config.mk.d"

# these are the defails used by CLI, which performs internal variable substitution
_DEFAULT_BASE_CONFIG_PATH_SINGLE_DIR = f"<curv-root-dir>/config/default.toml"
_DEFAULT_SCHEMA_TOML_PATH_SINGLE_DIR = f"<curv-root-dir>/config/schema.toml"
_DEFAULT_BASE_CONFIG_PATH_SEPARATE_DIRS = f"<curv-root-dir>/config/profiles/default.toml"
_DEFAULT_SCHEMA_TOML_PATH_SEPARATE_DIRS = f"<curv-root-dir>/config/schema/schema.toml"
def GET_DEFAULT_BASE_CONFIG_PATH() -> str:
    from curvtools.cli.curvcfg.cli_helpers.base_config_and_schema_mode import get_base_config_and_schema_mode, BaseConfigAndSchemaMode
    if get_base_config_and_schema_mode() == BaseConfigAndSchemaMode.BASE_CONFIG_AND_SCHEMA_IN_SINGLE_DIRECTORY:
        return _DEFAULT_BASE_CONFIG_PATH_SINGLE_DIR
    else:
        return _DEFAULT_BASE_CONFIG_PATH_SEPARATE_DIRS
def GET_DEFAULT_SCHEMA_TOML_PATH() -> str:
    from curvtools.cli.curvcfg.cli_helpers.base_config_and_schema_mode import get_base_config_and_schema_mode, BaseConfigAndSchemaMode
    if get_base_config_and_schema_mode() == BaseConfigAndSchemaMode.BASE_CONFIG_AND_SCHEMA_IN_SINGLE_DIRECTORY:
        return _DEFAULT_SCHEMA_TOML_PATH_SINGLE_DIR
    else:
        return _DEFAULT_SCHEMA_TOML_PATH_SEPARATE_DIRS

# output file paths
DEFAULT_DEP_FILE_PATH = f"<build-dir>/make.deps/{DEFAULT_DEP_FILE_NAME}"
DEFAULT_MERGED_TOML_PATH = f"<build-dir>/config/{DEFAULT_MERGED_TOML_NAME}"

# name of current profile file make include in config directory
CURRENT_PROFILE_MK_FILENAME = ".current_profile.mk"