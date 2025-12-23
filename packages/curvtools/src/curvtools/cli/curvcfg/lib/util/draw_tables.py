from __future__ import annotations
from typing import Union, Optional, Dict, List
from rich.padding import Padding, PaddingDimensions
from rich.panel import Panel
from rich.box import Box, ASCII_DOUBLE_HEAD, ROUNDED, ASCII2, SIMPLE, MINIMAL_DOUBLE_HEAD, MINIMAL, MINIMAL_HEAVY_HEAD
from rich.style import Style
from rich.table import Table
from rich.markup import escape
from rich.tree import Tree
from rich.text import Text
from pathlib import Path
from curvtools.cli.curvcfg.lib.globals.console import console
import click
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import FsPathType
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from curvtools.cli.curvcfg.lib.curv_paths import CurvPaths
from curvtools.cli.curvcfg.lib.globals.constants import PATHS_RAW_ENV_FILE_REL_PATH
from curvtools.cli.curvcfg.lib.util.config_parsing import SchemaOracle
from curvtools.cli.curvcfg.lib.util.config_parsing.parse_schema import SchemaScalarVar

def get_box(use_ascii_box: bool = False) -> Box:
    return ASCII2 if use_ascii_box else ROUNDED

def _extract_variable_info(schema_oracle: SchemaOracle) -> list[dict[str, Any]]:
    """
    Iterate over all variables in a SchemaOracle and extract their metadata.
    
    Returns a list of dicts, one per variable, with the following structure:
    {
        'var_name': str,               # e.g., 'CFG_CACHE_CACHELINES_LATENCY'
        'artifacts': list[str],        # e.g., ['SVPKG', 'MK', 'ENV', 'SVH']
        'display_mk': str,             # e.g., 'int'
        'display_sv': str,             # e.g., 'int'
        'domain_kind': str,            # 'none', 'choices', or 'range'
        'domain_choices': list | None, # e.g., [0, 1, 2] or None
        'domain_range': tuple | None,  # e.g., (0, 100) or None
        'domain_range_display': 
           tuple[str, str] | None,     # formatted range bounds using mk_display(), or None
        'default': Any | None,         # e.g., 0 or None
        'default_display': str | None, # formatted default using mk_display(), or None
        'parse_type': str,             # e.g., 'int', 'string', 'uint'
        'toml_path': str | None,       # e.g., 'cache.cachelines.latency'
    }
    """
    results = []
    
    # Iterate over all variables in the SchemaOracle
    for var_name, var in schema_oracle.items():
        # Only process scalar variables (skip array variables for this example)
        if not isinstance(var, SchemaScalarVar):
            continue
        
        # Extract artifacts list (convert Artifact enum to string)
        artifacts = [artifact.value for artifact in var.artifacts]
        
        # Extract display information
        display_mk = var._display_mk  # e.g., 'int'
        display_sv = var._display_sv  # e.g., 'int'
        
        # Extract domain information
        domain = var._domain
        domain_kind = domain.kind  # 'none', 'choices', or 'range'
        domain_choices = domain.choices  # list or None
        domain_range = domain.range  # tuple or None
        default = domain.default  # any value or None
        
        # Extract parse type
        parse_type = var._parse_type.value  # e.g., 'int', 'string', 'uint'
        
        # Extract toml_path
        toml_path = var.toml_path  # e.g., 'cache.cachelines.latency' or None
        
        # Format default value using mk_display() if it exists
        default_display = None
        if default is not None and var._display_mk is not None:
            default_display = var.mk_display(default)
        
        # Format domain_range bounds using mk_display() if it exists
        domain_range_display = None
        if domain_range is not None and var._display_mk is not None:
            lower, upper = domain_range
            domain_range_display = (var.mk_display(lower), var.mk_display(upper))
        
        # Build the result dict
        var_info = {
            'var_name': var_name,
            'artifacts': artifacts,
            'display_mk': display_mk,
            'display_sv': display_sv,
            'domain_kind': domain_kind,
            'domain_choices': domain_choices,
            'domain_range': domain_range,
            'domain_range_display': domain_range_display,
            'default': default,
            'default_display': default_display,
            'parse_type': parse_type,
            'toml_path': toml_path,
            'value': var.mk_display() if var._display_mk is not None else None
        }
        results.append(var_info)
    return results

def display_merged_toml_table(
    schema_oracle: SchemaOracle, 
    merged_toml_path: Path, 
    use_ascii_box: bool = False, 
    verbose_table: bool = False
) -> None:
    """
    Display the merged TOML table.
    
    Args:
        schema_oracle: the schema oracle
        merged_toml_path: the merged toml path as a string
        verbose_table: whether to display the verbose table

    Returns:
        None
    """
    # Color helpers
    def get_color_for_makefile_type(makefile_type: str | None) -> dict[str, str]:
        color_for_makefile_type = {
            "int": {"open": "[yellow]", "close": "[/yellow]"},
            "uint": {"open": "[bold red]", "close": "[/bold red]"},
            "string": {"open": "[bold white]", "close": "[/bold white]"},
            "default": {"open": "[bold green]", "close": "[/bold green]"},
            "_magenta": {"open": "[magenta2]", "close": "[/magenta2]"},
            "_blue": {"open": "[blue]", "close": "[/blue]"},
        }
        if makefile_type is not None and makefile_type in color_for_makefile_type:
            return color_for_makefile_type[makefile_type]
        return color_for_makefile_type["default"]
    def colorize_key(s: str, color: str = "bold yellow") -> str:
        return f"[{color}]" + s + f"[/{color}]"
    def colorize_value(makefile_type: str, s: str) -> str:
        m = get_color_for_makefile_type(makefile_type)
        return m["open"] + s + m["close"]

    from curvtools.cli.curvcfg.lib.curv_paths import CurvPaths
    table_options = {}
    table_options["box"] = get_box(use_ascii_box)
    TitleWithSourceText = Text.assemble(
        Text("Variable Values\n", style="bold white"),
        Text("(source: "),
        Text(f"{merged_toml_path}", style="bold green"),
        Text(")")
    )
    TitleText = Text("Variable Values", style="bold white")

    if verbose_table:
        table_options["title"] = TitleWithSourceText
        table = Table(expand=False, **table_options)
        table.add_column(f"Variable", overflow="fold")
        table.add_column("Value", overflow="fold")
        table.add_column("Type", overflow="fold")
        table.add_column("Constraints", overflow="fold", max_width=40)
        table.add_column("Locations", overflow="fold")
        var_infos = _extract_variable_info(schema_oracle)
        for var_info in var_infos:
            artifacts_str = ", ".join(var_info['artifacts'])
            domain_str = ""#f"{var_info['domain_kind']}: "
            if var_info['domain_choices'] is not None:
                domain_str += f"{var_info['domain_choices']}"
            elif var_info['domain_range_display'] is not None:
                domain_str += f"{var_info['domain_range_display'][0]} - {var_info['domain_range_display'][1]}"
            else:
                domain_str = "*"
            table.add_row(
                f"{colorize_key(var_info['var_name'])}\n{var_info['toml_path']}",
                f"{colorize_value(var_info['parse_type'], str(var_info['value']))}",
                colorize_value(var_info['parse_type'], var_info['parse_type']),
                colorize_value(var_info['parse_type'], domain_str),
                colorize_value("_magenta", artifacts_str),
            )
    else:
        table_options["title"] = TitleText
        table = Table(expand=False, **table_options)
        table.add_column(f"Variable", overflow="fold")
        table.add_column("Value", overflow="fold")
        var_infos = _extract_variable_info(schema_oracle)
        for var_info in var_infos:
            table.add_row(
                f"{colorize_key(var_info['var_name'])}\n{var_info['toml_path']}",
                f"{colorize_value(var_info['display_mk'], str(var_info['value']))}",
            )
    console.print(table)
    console.print()


###############################################################################
#
# Display config.mk.d contents helper
#
###############################################################################

def display_dep_file_contents(contents: str, target_path: FsPathType, use_ascii_box: bool = False) -> None:
    """
    Display the dep file contents.
    
    Args:
        contents: the contents of the dep file
        target_path: the target path
        use_ascii_box: whether to use ascii box

    Returns:
        None
    """
    title = target_path.mk_rel_to_cwd()
    box=get_box(use_ascii_box)
    p = Panel(contents, 
        title=f"[bold green]{title}[/bold green]", 
        border_style=Style(color="cyan", bold=True),
        expand=False, 
        box=box)
    console.print(p)
    console.print()

###############################################################################
#
# debugging tables
#
###############################################################################

def display_tool_settings(curvctx: CurvContext, use_ascii_box: bool = False):
    # print the tool's config settings
    curvcfg_settings_path = curvctx.args.get('curvcfg_settings_path', None)
    curvcfg_settings = curvctx.args.get('curvcfg_settings', None)
    if curvcfg_settings is not None:
        if curvcfg_settings_path is not None:
            title: Optional[Text]= Text.assemble(
                Text("Tool Settings\n", style="bold white"),
                Text("(source: "),
                Text(f"{curvcfg_settings_path}", style="bold green"),
                Text(")")
            )
        else:
            title: Optional[Text]= Text("Tool Settings", style="bold white")
        table = Table(
            expand=False, 
            highlight=True, 
            border_style="blue",
            title=title,
            box=MINIMAL_HEAVY_HEAD if not use_ascii_box else ASCII2,
            pad_edge=False,
            )
        table.add_column("Setting")
        table.add_column("Value", overflow="fold")
        for key, value in curvcfg_settings.items():
            table.add_row(f"{key}", str(value))
        p = Panel(table, 
                title=f"[blue]tool settings[/blue]", 
                border_style="blue",
                highlight=True,
                padding=0,
                box=get_box(use_ascii_box),
                expand=False,
                )
        console.print(p)
        console.print()

def display_curvpaths(curv_paths: CurvPaths, use_ascii_box: bool = False) -> None:
    """
    Display the curvpaths.
    
    Args:
        curv_paths: the curv paths instance
        use_ascii_box: whether to use ascii box

    Returns:
        None
    """
    table = Table(
            expand=False, 
            highlight=True, 
            border_style="blue",
            title=f"[bold blue]{PATHS_RAW_ENV_FILE_REL_PATH}[/bold blue]",
            box=MINIMAL_HEAVY_HEAD if not use_ascii_box else ASCII2,
            pad_edge=False,
            )
    table.add_column("Path Name", overflow="fold", highlight=False)
    table.add_column("Value", overflow="fold", highlight=False, style="deep_pink4")
    table.add_column("Resolved", overflow="fold", highlight=False)
    for key, value in sorted(curv_paths.items()):
        key_table = Table.grid()
        key_table.add_column("Key", overflow="fold", highlight=False)
        key_table.add_row(f"{key}")
        key_table.add_row(f"{value.uninterpolated_value}", style="dark_magenta")
        table.add_row(
            key_table,
            str(value),
            "[green]yes[/green]" if value.is_fully_resolved() else "[red]no[/red]",
            end_section=True,
    )
    console.print(table)
    console.print()

def display_args_table(args: dict[str, Any], title: str, use_ascii_box: bool = False):
    NoneText = Text("None", style="bold red")

    # print the effective arguments
    table = Table(expand=False, 
        highlight=True, 
        border_style="yellow",
        #title=f"[yellow]effective arguments ([bold]{title}[/bold] command)[/yellow]",
        box=MINIMAL_HEAVY_HEAD if not use_ascii_box else ASCII2,
        pad_edge=False,
        )
    table.add_column("Argument")
    table.add_column("Value", overflow="fold")
    for key, value in args.items():
        if value is None:
            table.add_row(f"{key}", NoneText)
        elif isinstance(value, list):
            table.add_row(f"{key}", str(value[0]))
            for item in value[1:]:
                table.add_row("", str(item))
        else:
            table.add_row(f"{key}", str(value))

    p2 = Panel(table, 
            title=f"[yellow]effective arguments ([bold]{title}[/bold] command)[/yellow]", 
            border_style="yellow",
            highlight=True,
            padding=0,
            box=get_box(use_ascii_box),
            expand=False,
            )
    console.print(p2)

def display_profiles_table(profile_name_and_path_list: list[tuple[str, Path]], curv_root_dir: Path, use_ascii_box: bool = False) -> None:
    """
    Display the profiles table.
    """
    s = f"CURV_ROOT_DIR = {curv_root_dir}"
    table = Table(expand=False, box=get_box(use_ascii_box), pad_edge=False, caption=f"{s}", caption_style="bold bright_green", width=len(s)+4)
    table.add_column("Profile Name")
    table.add_column("Profile Path", overflow="fold")
    for profile_name, profile_path in profile_name_and_path_list:
        table.add_row(profile_name, str(profile_path))
    console.print(table)
    console.print()

def display_default_map(default_map: dict[str, Any], use_ascii_box: bool = False):
    from rich.pretty import Pretty
    pretty_content = Pretty(default_map, expand_all=True)
    p = Panel(pretty_content, title="Default Map", border_style="blue", highlight=True, padding=(0, 1), box=get_box(use_ascii_box), expand=False)
    console.print(p)
    console.print()