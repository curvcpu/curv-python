PROGRAM_NAME = "curvcfg"
PACKAGE_NAME = "curvtools"

# output files from merge command
DEFAULT_MERGED_TOML_NAME = "merged.toml"
DEFAULT_OVERLAY_TOML_NAME = "overlay.toml"
DEFAULT_DEP_FILE_NAME = "config.mk.d"

DEFAULT_DEP_FILE_DIR = f"make.deps"
DEFAULT_MERGED_TOML_DIR = f"config"

# these are the defails used by CLI, which performs internal variable substitution
DEFAULT_PROFILE_TOML_PATH = f"<curv-root-dir>/config/profiles/default.toml"
DEFAULT_SCHEMA_TOML_PATH = f"<curv-root-dir>/config/schema/schema.toml"

# output file paths
DEFAULT_DEP_FILE_PATH = f"<build-dir>/{DEFAULT_DEP_FILE_DIR}/{DEFAULT_DEP_FILE_NAME}"
DEFAULT_MERGED_TOML_PATH = f"<build-dir>/{DEFAULT_MERGED_TOML_DIR}/{DEFAULT_MERGED_TOML_NAME}"
