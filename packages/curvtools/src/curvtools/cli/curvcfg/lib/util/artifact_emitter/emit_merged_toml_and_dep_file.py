from __future__ import annotations
from pathlib import Path
from typing import Optional, Any
from curvtools.cli.curvcfg.lib.globals.curvpaths import CurvPaths
from curvtools.cli.curvcfg.lib.util.artifact_emitter import emit_dep_file
import curvpyutils.tomlrw as tomlrw
from curvpyutils.file_utils import open_write_iff_change

__all__ = ["emit_merged_toml_and_dep_file"]

def emit_merged_toml_and_dep_file(
        curvpaths: CurvPaths,

        combined_schema: dict[str, Any], 
        schema_src_paths: list[Path],
        merged_config: dict[str, Any],
        config_src_paths: list[Path],

        merged_toml_out_path: Path,
        mk_dep_out_path: Path,

        verbosity: int = 0,
        overwrite_only_if_changed: bool = True,
        header_comment: Optional[str] = None,
    ) -> tuple[bool, bool]:
    """
    Generic function for emitting a merged toml and a dep file based on a 
    combined schema dict and a merged config vars dict.

    Currently, this is called twice to make:
        - merged_board.toml + board.mk.d
        - merged_config.toml + config.mk.d

    Args:
        combined_schema: the combined schema (input dict[str, Any])
        schema_src_paths: the list of schema source paths (input list[Path])
        merged_config: the merged config (input dict[str, Any])
        config_src_paths: the list of config source paths (input list[Path])
        merged_toml_out_path: the path to the output TOML file (output Path)
        dep_file_out_path: the path to the output dep file (output Path)
        verbosity: the verbosity level (input int)
        overwrite_only_if_changed: whether to overwrite only if the file has changed (default True)
        header_comment: an optional header comment to add to the top of the merged board configuration TOML file (input str)
    Returns:
        tuple[bool, bool]: True if the merged TOML file was overwritten, False if it was not. 
            and True if the dep file was overwritten, False if it was not.
    """

    general_header_comment = """\
########################################################
# Machine-generated file; do not edit
########################################################
"""
    schema_header_comment = """
########################################################
#
# Schema section
#
########################################################

"""
    merged_config_header_comment = """
########################################################
#
# Configuration section
#
########################################################

"""

    # Build the content as a string, canonicalizing each TOML section
    parts = []
    if header_comment and header_comment.strip():
        parts.append('# ' + header_comment.strip("\n") + '\n\n')
    parts.append(general_header_comment)
    parts.append(merged_config_header_comment)
    parts.append(tomlrw.dumps(merged_config, should_canonicalize=True))
    parts.append(schema_header_comment)
    parts.append(tomlrw.dumps(combined_schema, should_canonicalize=True))
    parts.append('\n')

    content = "".join(parts)

    cm = open_write_iff_change(merged_toml_out_path, "w", force_overwrite=not overwrite_only_if_changed)
    with cm as f:
        f.write(content)

    merged_toml_overwritten = bool(cm.changed)
    dep_file_overwritten = False

    # if mk_dep_out_path is not provided, we don't
    # emit one but also raise no error
    if mk_dep_out_path is not None:
        dep_file_overwritten = emit_dep_file(
            target_path=merged_toml_out_path,
            dependency_paths=schema_src_paths + config_src_paths,
            dep_file_out_path=mk_dep_out_path,
            curvpaths=curvpaths,
            header_comment=header_comment,
            write_only_if_changed=overwrite_only_if_changed,
            verbosity=verbosity,
        )

    return merged_toml_overwritten, dep_file_overwritten

# def emit_final_merged_toml(
#     curvpaths: CurvPaths,

#     merged_tomls_path_list: list[Path],

#     merged_toml_out_path: Path,

#     verbosity: int = 0,
#     overwrite_only_if_changed: bool = True,
#     header_comment: Optional[str] = None,
# ) -> bool:
#     """
#     Writes a final `merged.toml`:
#         1.  merged_board.toml
#         2.  merged_config.toml
#     (These names are the commonly used names, but are not required to
#     be named this way. The only requirement is to combine the files in 
#     merged_tomls_path_list irrespective of the names of the files.)

#     No dep produced file b/c the main makefiles already track that merged.toml depends on all
#     intermediate/*.toml files.

#     The merge works like this:
#       -  Every file in merged_tomls_path_list is split
#       by top-level key into three dictionaries:
#         1 _schema.*
#         2 _metadata.*
#         3 (everything else)
#     Currently, we don't do anything with the _metadata.* 
#     dictionary, but it may be used in the future.

#     The _schema.* dictionaries are combined into a 
#     single dict[str, Any]. If two files have the same
#     key, KeyError is raised per the rules below.

#     The (everything else) dictionary is combined into a 
#     single dict[str, Any]. Because these values have
#     already undergone a deep merge, duplicate keys also
#     raise KeyError per the rules below.

#     KeyError rules:
#       - For _schema.*:  it is an error to have a conflict
#       at the third level, i.e., two _schema.vars.VAR_NAME's
#       are an error, but it is not a problem to have 
#       _schema.vars.VAR_NAME1 and _schema.vars.VAR_NAME2.
#       - _schema.arrays.* are treated the same way.
#       - For the "everything else" dictionary: it 
#       is an error to have a full path duplicate key. So,
#       it is legal to have cpu.xlen and cpu.xlen2, but it
#       is not legal to have two top-level cpu.xlen keys,
#       even if their values are the same.
    
#     Mergeing:
#       - At the end, we are left with two dicts which are 
#       passed to emit_merged_toml_and_dep_file(). No file
#       paths are passed since we don't need to produce a 
#       dep file for the merged TOML.
#       - The merged.toml file's name and output path comes 
#       from CurvPaths["DEFAULT_MERGED_TOML_PATH"].
    
#     Returns:
#         bool: True if the merged TOML file was overwritten, 
#         False if it was not.
#     """

#     SCHEMA_KEY = "_schema"
#     METADATA_KEY = "_metadata"

#     combined_schema: dict[str, Any] = {}
#     combined_config: dict[str, Any] = {}
#     # No metadata dict is generated because we don't currently
#     # have an algorithm for handling duplicate metadata keys,
#     # and every input file has essentially the same metadata
#     # just with different values.

#     # Split each file on top level key to generate combined_schema and combined_config
#     for merged_toml_path in merged_tomls_path_list:
#         toml_dict = tomlrw.loadf(merged_toml_path)

#         for top_key, top_value in toml_dict.items():
#             if top_key == SCHEMA_KEY:
#                 # Merge schema at the third level (e.g., _schema.vars.VAR_NAME)
#                 # It's an error to have duplicate keys at third level
#                 for second_key, second_value in top_value.items():
#                     if second_key not in combined_schema:
#                         combined_schema[second_key] = {}
#                     for third_key, third_value in second_value.items():
#                         if third_key in combined_schema[second_key]:
#                             raise KeyError(
#                                 f"Duplicate key at {SCHEMA_KEY}.{second_key}.{third_key} "
#                                 f"found in {merged_toml_path}"
#                             )
#                         combined_schema[second_key][third_key] = third_value
#             elif top_key == METADATA_KEY:
#                 # Skip metadata for now
#                 pass
#             else:
#                 # Config keys - error on any duplicate top-level key
#                 if top_key in combined_config:
#                     raise KeyError(
#                         f"Duplicate config key '{top_key}' found in {merged_toml_path}"
#                     )
#                 combined_config[top_key] = top_value

#     # Wrap combined_schema with the _schema key since emit_merged_toml_and_dep_file
#     # expects the full schema dict structure (i.e., {_schema: {vars: ..., arrays: ...}})
#     wrapped_schema = {SCHEMA_KEY: combined_schema} if combined_schema else {}

#     # Call emit_merged_toml_and_dep_file once with the combined dicts
#     merged_toml_overwritten, _ = emit_merged_toml_and_dep_file(
#         curvpaths=curvpaths,
#         combined_schema=wrapped_schema,
#         schema_src_paths=[],
#         merged_config=combined_config,
#         config_src_paths=[],
#         merged_toml_out_path=merged_toml_out_path,
#         mk_dep_out_path=None,
#         verbosity=verbosity,
#         overwrite_only_if_changed=overwrite_only_if_changed,
#         header_comment=header_comment,
#     )

#     return merged_toml_overwritten
