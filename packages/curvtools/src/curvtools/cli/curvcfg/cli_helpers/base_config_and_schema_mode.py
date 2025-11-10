from enum import Enum
from pathlib import Path

class BaseConfigAndSchemaMode(Enum):
    BASE_CONFIG_AND_SCHEMA_IN_SINGLE_DIRECTORY = "base_config_and_schema_in_single_directory"
    BASE_CONFIG_AND_SCHEMA_IN_SEPARATE_DIRECTORIES = "base_config_and_schema_in_separate_directories"

_BASE_CONFIG_AND_SCHEMA_MODE: BaseConfigAndSchemaMode | None = None

def _profiles_and_schema_dirs_exist() -> tuple[bool, bool]:
    """
    Determines whether $CURV_ROOT_DIR/config/profiles and $CURV_ROOT_DIR/config/schema directories exist.
    """

    from curvpyutils.cli_util import preparse, EarlyArg
    early_curv_root_dir = EarlyArg(["--curv-root-dir"], env_var_fallback="CURV_ROOT_DIR")
    preparse([early_curv_root_dir])
    if not early_curv_root_dir.value:
        return False, False
    else:
        curv_root_dir = early_curv_root_dir.value
        try:
            profiles_dir_exists = (Path(curv_root_dir) / "config" / "profiles").is_dir()
            schema_dir_exists = (Path(curv_root_dir) / "config" / "schema").is_dir()
        except:
            profiles_dir_exists = False
            schema_dir_exists = False
        return profiles_dir_exists, schema_dir_exists

def get_base_config_and_schema_mode() -> BaseConfigAndSchemaMode:
    """
    Determines the base and schema mode based on whether $CURV_ROOT_DIR/config/profiles and $CURV_ROOT_DIR/config/schema directories exist.
    """
    global _BASE_CONFIG_AND_SCHEMA_MODE
    if _BASE_CONFIG_AND_SCHEMA_MODE is not None:
        # print(f"❤️ BASE_CONFIG_AND_SCHEMA_MODE is not None: {BASE_CONFIG_AND_SCHEMA_MODE}")
        return _BASE_CONFIG_AND_SCHEMA_MODE
    
    profiles_dir_exists, schema_dir_exists = _profiles_and_schema_dirs_exist()
    if not profiles_dir_exists or not schema_dir_exists:
        _BASE_CONFIG_AND_SCHEMA_MODE = BaseConfigAndSchemaMode.BASE_CONFIG_AND_SCHEMA_IN_SINGLE_DIRECTORY
    else:
        _BASE_CONFIG_AND_SCHEMA_MODE = BaseConfigAndSchemaMode.BASE_CONFIG_AND_SCHEMA_IN_SEPARATE_DIRECTORIES
    return _BASE_CONFIG_AND_SCHEMA_MODE
