from __future__ import annotations
from enum import Flag
from pathlib import Path
from typing import NamedTuple
import os
import sys
from typing import Any, Dict, Tuple
from curvpyutils.toml_utils import MergedTomlDict  # type: ignore
from curvtools.cli.curvcfg.lib.util.cfgvalue import CfgValue, CfgValues, MissingVars
from curvpyutils.file_utils.repo_utils import get_git_repo_root
from curvtools.cli.curvcfg.lib.util import FileEmitter, ConfigFileTypes, ConfigFileTypesForWriting

MAX_INT = 2**32 - 1

# --- helpers ------------------------------------------------------------------

def validate_and_collect(cfg:Dict[str, Any], schema:Dict[str, Any]) -> Tuple[CfgValues, MissingVars]:
    """
    Checks a base config TOML dict against and a schema TOML file, validates, and returns the validated config values and metadata.
    
    Returns tuple of:
        - vals: CfgValues           - var_name -> CfgValue with additional 'meta' attribute for schema metadata
        - missing_vars: MissingVars - list of schema var_names that were not found in the config (but may have been filled in by a default value)
    """

    # ------------------------------------------------------------
    #
    # Internal helper functions
    #
    # ------------------------------------------------------------

    def get_by_path(d:Dict[str, Any], path:str, default:str | int | None=None, required:bool=True) -> Tuple[Any, bool]: # returns (value, found)
        cur = d
        for part in path.split("."):
            if part not in cur:
                if required and default is None:
                    raise KeyError("Missing '{}' while resolving '{}'".format(part, path))
                else:
                    return default, False
            cur = cur[part]
        return cur, True

    def parse_int_like(x:Any) -> int:
        # Accept ints, hex strings like "0x1234", binary "0b...", octal "0o...", or decimal strings
        if isinstance(x, int):
            return x
        if isinstance(x, str):
            s = x.strip().lower()
            if s.startswith("0x") or s[:2].startswith("'h"):
                return int(s, 16)
            if s.startswith("0b") or s[:2].startswith("'b") or s.endswith("b"):
                return int(s, 2)
            return int(s, 10)
        raise TypeError("Expected int or string, got {} ({!r})".format(type(x), x))

    def is_int_enum(enum_vals:list[int | str]) -> bool:
        return isinstance(enum_vals, list) and all(isinstance(v, int) for v in enum_vals)

    def is_str_enum(enum_vals:list[int | str]) -> bool:
        return isinstance(enum_vals, list) and all(isinstance(v, str) for v in enum_vals)

    def get_default(entry:Dict[str, Any]) -> int | str | None:
        """
        Returns the default value for an entry in the schema.

        If the default value is not specified, returns None.
        """
        if entry["type"] == "int":
            d = entry.get("default", None)
            return int(d) if d is not None else None
        elif entry["type"] == "string":
            d = entry.get("default", None)
            return str(d) if d is not None else None
        elif entry["type"] == "enum":
            enum_vals = entry.get("enum_values")
            if is_int_enum(enum_vals):
                d = entry.get("default", None)
                return int(d) if d is not None else None
            else:
                d = entry.get("default", None)
                return str(d) if d is not None else None
        else:
            return None

    # ------------------------------------------------------------
    #
    # Main logic
    #
    # ------------------------------------------------------------

    schema_root = schema.get("_schema", {}) if isinstance(schema.get("_schema", {}), dict) else {}
    vars_dict = schema_root.get("vars") if isinstance(schema_root.get("vars"), dict) else None
    consts_dict = schema_root.get("consts") if isinstance(schema_root.get("consts"), dict) else None
    has_vars = vars_dict is not None
    has_consts = consts_dict is not None
    if not has_vars and not has_consts:
        raise ValueError("schema.toml must have a [vars] or [consts] table or both")

    schema_entries: Dict[str, Any] = {}
    if has_vars:
        schema_entries.update(vars_dict)
    if has_consts:
        schema_entries.update(consts_dict)

    vals:Dict[str, str | int | None] = {}
    meta:Dict[str, Dict[str, str | int | None]] = {}
    missing_vars:list[str] = []

    for _, schema_entry in schema_entries.items():
        toml_path = schema_entry["toml_path"]
        var_name  = schema_entry["var_name"]
        value_type     = schema_entry["type"]
        locations = schema_entry.get("locations", "all")
        sv_type   = schema_entry.get("sv_type")
        makefile_type = schema_entry.get("makefile_type")
        default = get_default(schema_entry)

        raw, found = get_by_path(cfg, toml_path, default, required=True)
        if not found:
            missing_vars.append(var_name)

        if value_type == "int":
            mn = schema_entry.get("min", 0)
            mx = schema_entry.get("max", MAX_INT)
            int_value = parse_int_like(raw)
            if int_value < int(mn):
                raise ValueError("{}: {} < min {}".format(var_name, int_value, mn))
            if int_value > int(mx):
                raise ValueError("{}: {} > max {}".format(var_name, int_value, mx))
            vals[var_name] = int_value

        elif value_type == "string":
            if not isinstance(raw, str):
                raise ValueError("{}: expected string, got {}".format(var_name, type(raw)))
            str_value = raw.strip()
            # for location makefiles, we cannot accept quoted strings
            if any(loc in locations for loc in ("makefiles","all")) and ('"' in str_value or "'" in str_value):
                # if it's just quotes around a string that contains no spaces or special characters,
                # simply strip the quotes
                if str_value.startswith('"') and str_value.endswith('"') and all(c not in str_value[1:-1] for c in ' \t\n\r\f\v'):
                    str_value = str_value[1:-1]
                elif str_value.startswith("'") and str_value.endswith("'") and all(c not in str_value[1:-1] for c in ' \t\n\r\f\v'):
                    str_value = str_value[1:-1]
                else:
                    raise ValueError("{}: quoted strings with spaces or special characters inside are not allowed for location 'makefiles'".format(var_name))
            vals[var_name] = str_value

        elif value_type == "enum":
            enum_vals = schema_entry.get("enum_values")
            if not (isinstance(enum_vals, list) and len(enum_vals) > 0):
                raise ValueError("{}: enum requires non-empty enum_values:  type of enum_vals={}, len(enum_vals)={}, enum_vals={}".format(var_name, type(enum_vals), len(enum_vals), enum_vals))
            if is_int_enum(enum_vals):
                int_value = parse_int_like(raw)
                if int_value not in enum_vals:
                    raise ValueError("{}: {} not in enum_values {}".format(var_name, int_value, enum_vals))
                vals[var_name] = int_value
            elif is_str_enum(enum_vals):
                if not isinstance(raw, str):
                    raise ValueError("{}: expected string for enum, got {}".format(var_name, type(raw)))
                str_value = raw.strip()
                # for location makefiles, we cannot accept quoted strings
                if any(loc in locations for loc in ("makefiles","all")) and ('"' in str_value or "'" in str_value):
                    # if it's just quotes around a string that contains no spaces or special characters,
                    # simply strip the quotes
                    if str_value.startswith('"') and str_value.endswith('"') and all(c not in str_value[1:-1] for c in ' \t\n\r\f\v'):
                        str_value = str_value[1:-1]
                    elif str_value.startswith("'") and str_value.endswith("'") and all(c not in str_value[1:-1] for c in ' \t\n\r\f\v'):
                        str_value = str_value[1:-1]
                    else:
                        raise ValueError("{}: quoted strings with spaces or special characters inside are not allowed for location 'makefiles'".format(var_name))
                if str_value not in enum_vals:
                    raise ValueError("{}: {!r} not in enum_values {}".format(var_name, str_value, enum_vals))
                vals[var_name] = str_value
            else:
                raise ValueError("{}: enum_values must be homogeneous (all int or all string)".format(var_name))
        
        else:
            raise ValueError("{}: unknown type '{}'".format(var_name, value_type))

        meta[var_name] = {
            "sv_type": sv_type,
            "makefile_type": makefile_type,
            "locations": locations,
            "type": value_type,
            "toml_path": toml_path,
            "is_default": True if found else False,
        }

    # Cross-field constraints hook (no-op for now)
    for rule in schema.get("constraints", {}).get("rules", []):
        _ = rule  # placeholder

    # Turns vals+meta into a collection type CfgValues which is a dictionary of str->CfgValue
    cfg_values = {}
    for var_name, val in vals.items():
        cfg_values[var_name] = CfgValue(val, meta[var_name], schema_entries[var_name])

    return CfgValues(cfg_values), MissingVars(missing_vars)

def get_config_values(config: str | Path | Dict[str, Any], schema: str | Path | Dict[str, Any] | None, is_combined_toml: bool) -> CfgValues:
    """
    Generates the configuration based on a base config TOML file and a schema TOML file.

    Args:
        config: The base config TOML, either as a file path (string or Path) or a dictionary.
        schema: The schema TOML, either as a file path (string or Path) or a dictionary.
        is_combined_toml: If True, the config argument is the path to a combined TOML file containing both the base config and the schema,
            and the schema argument is unused.

    Return value:
        - vals: Dict[str, CfgValue]
        The validated config values as a dictionary of str->CfgValue.
    """
    if is_combined_toml:
        if isinstance(config, str) or isinstance(config, Path):
            combined_toml_dict:MergedTomlDict = MergedTomlDict.from_toml_files(str(config))
        else:
            combined_toml_dict:MergedTomlDict = MergedTomlDict.from_dict(config)
        schema_dict, config_dict = combined_toml_dict.split_on_top_level_key("_schema")
        config_values, _ = validate_and_collect(config_dict, schema_dict)
    else:
        if isinstance(config, str) or isinstance(config, Path):
            config_dict:MergedTomlDict = MergedTomlDict.from_toml_files(str(config))
        else:
            config_dict:MergedTomlDict = MergedTomlDict.from_dict(config)
        if isinstance(schema, str) or isinstance(schema, Path):
            schema_dict:MergedTomlDict = MergedTomlDict.from_toml_files(str(schema))
        else:
            schema_dict:MergedTomlDict = MergedTomlDict.from_dict(schema)
        config_values, _ = validate_and_collect(config_dict, schema_dict)
    return config_values

def emit_config_files(config_values: CfgValues,
                      outdir_path: str, 
                      emit_files: ConfigFileTypes = ConfigFileTypesForWriting, 
                      verbosity: int = 0) -> tuple[list[str], list[str]]:
    """
    Emits the configuration files to the specified output directory.

    Args:
        config_values: The validated config values.
        outdir_path: The path to the output directory.
        emit_files: A set of OR'd flags indicating which files to emit. If NONE (=0), nothing 
            is written to disk, though the validated config values and metadata are still returned.
        verbosity: The verbosity level.

    Returns:
        tuple of:
            - files_emitted: list[str] - list of files that were emitted
            - files_unchanged: list[str] - list of files that were not emitted because they were unchanged

    Side effect:
        Assuming emit_files is not set to ConfigFileTypes.NONE, the following files may be emitted:
        to <outdir_path>:
        - curv.mk          (Makefile variables)
        - curvcfgpkg.sv    (SystemVerilog package with typed localparams)
        - curvcfg.svh      (SV `define macros with include guards)
        - curvcfg.json     (flat JSON object)
        - .curv.env        (shell environment variables)

        Files are only written if they would be different from the pre-existing files.
    """
    emitter = FileEmitter(config_values, 
                          outdir_path, 
                          emit_files,
                          verbosity=verbosity)
    files_emitted, files_unchanged = emitter.emit(write_only_if_changed=True)
    return files_emitted, files_unchanged