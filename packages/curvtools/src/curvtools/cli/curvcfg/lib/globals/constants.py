PROGRAM_NAME = "curvcfg"
PACKAGE_NAME = "curvtools"

# output files from merge command
DEFAULT_MERGED_TOML_NAME = "merged.toml"
DEFAULT_OVERLAY_TOML_NAME = "overlay.toml"
DEFAULT_DEP_FILE_NAME = "config.mk.d"

# these are the defails used by CLI, which performs internal variable substitution
DEFAULT_PROFILE_TOML_PATH = f"<curv-root-dir>/config/profiles/default.toml"
DEFAULT_SCHEMA_TOML_PATH = f"<curv-root-dir>/config/schema/schema.toml"

# output file paths
DEFAULT_DEP_FILE_PATH = f"<build-dir>/make.deps/{DEFAULT_DEP_FILE_NAME}"
DEFAULT_MERGED_TOML_PATH = f"<build-dir>/config/{DEFAULT_MERGED_TOML_NAME}"
