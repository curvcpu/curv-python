from __future__ import annotations
from typing import Union, Optional, Dict, List
from curvtools.cli.curvcfg.lib.util.cfgvalue import CfgValues
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
    from curvtools.cli.curvcfg.lib.globals.curvpaths import CurvPaths
from curvtools.cli.curvcfg.lib.globals.constants import PATHS_RAW_ENV_FILE_REL_PATH

def get_box(use_ascii_box: bool = False) -> Box:
    return ASCII2 if use_ascii_box else ROUNDED

###############################################################################
#
# Display merged TOML table helper
#
###############################################################################

def display_merged_toml_table(config_values: CfgValues, merged_toml_path: str, use_ascii_box: bool = False, verbose_table: bool = False) -> None:
    """
    Display the merged TOML table.
    
    Args:
        config_values: the config values
        merged_toml_path: the merged toml path as a string
        verbose_table: whether to display the verbose table

    Returns:
        None
    """
    # Color helpers copied from existing CLI display
    color_for_makefile_type = {
        "decimal": {"open": "[yellow]", "close": "[/yellow]"},
        "hex32": {"open": "[green]", "close": "[/green]"},
        "hex16": {"open": "[green]", "close": "[/green]"},
        "hex8": {"open": "[green]", "close": "[/green]"},
        "hex": {"open": "[green]", "close": "[/green]"},
        "string": {"open": "[bold white]", "close": "[/bold white]"},
        "default": {"open": "[white]", "close": "[/white]"},
        "int": {"open": "[bold magenta]", "close": "[/bold magenta]"},
        "int enum": {"open": "[bold red]", "close": "[/bold red]"},
        "string enum": {"open": "[bold green]", "close": "[/bold green]"},
        "string": {"open": "[bold white]", "close": "[/bold white]"},
    }
    def colorize_key(s: str, color: str = "bold yellow") -> str:
        return f"[{color}]" + s + f"[/{color}]"
    def colorize_value(makefile_type: str, s: str) -> str:
        m = color_for_makefile_type.get(makefile_type, color_for_makefile_type["default"])
        return m["open"] + s + m["close"]

    from curvtools.cli.curvcfg.lib.globals.curvpaths import CurvPaths
    table_options = {}
    table_options["box"] = get_box(use_ascii_box)
    table_options["caption"] = f"config hash: {config_values.hash()}"
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
        for k in sorted(config_values.keys()):
            v = config_values[k]
            table.add_row(
                f"{colorize_key(k)}\n{v.meta.toml_path}",
                f"{colorize_value(v.meta.makefile_type, str(v))}",
                colorize_value(v.schema_meta.get_type_str()[0], v.schema_meta.get_type_str()[0]),
                colorize_value(v.schema_meta.get_type_str()[1], v.schema_meta.get_type_str()[1]),
                v.locations_str(),
            )
    else:
        table_options["title"] = TitleText
        table = Table(expand=False, **table_options)
        table.add_column(f"Variable", overflow="fold")
        table.add_column("Value", overflow="fold")
        for k in sorted(config_values.keys()):
            v = config_values[k]
            table.add_row(
                f"{colorize_key(k)}",
                f"{colorize_value(v.meta.makefile_type, str(v))}",
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