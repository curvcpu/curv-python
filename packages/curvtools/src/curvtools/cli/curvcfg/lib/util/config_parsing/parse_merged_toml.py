from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import curvpyutils.tomlrw as tomlrw

from .parse_schema import parse_dict_to_schema_vars, SchemaOracle, SCHEMA_ROOT_KEY


def schema_oracle_from_merged_toml(merged_toml: Path) -> SchemaOracle:
    """
    Build a SchemaOracle from a merged TOML file.
    """
    merged_dict: Mapping[str, Any] = tomlrw.loadf(merged_toml)

    schema_dict = parse_dict_to_schema_vars(merged_dict, merged_toml)
    schema_oracle = SchemaOracle(vars_by_name=schema_dict)

    config_root = {k: v for k, v in merged_dict.items() if k != SCHEMA_ROOT_KEY}
    schema_oracle.feed_config(config_root)

    return schema_oracle
