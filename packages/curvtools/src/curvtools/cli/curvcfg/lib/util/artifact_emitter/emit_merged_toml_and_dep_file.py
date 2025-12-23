from __future__ import annotations
from pathlib import Path
from typing import Optional, Any
from curvtools.cli.curvcfg.lib.curv_paths import CurvPaths
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
