from typing import Union, Optional, Dict, List
from curvtools.cli.curvcfg.lib.util.cfgvalue import CfgValues
from rich.padding import Padding, PaddingDimensions
from rich.panel import Panel
from rich.box import Box, ASCII_DOUBLE_HEAD, ROUNDED, ASCII2, SIMPLE, MINIMAL_DOUBLE_HEAD, MINIMAL, MINIMAL_HEAVY_HEAD
from rich.style import Style
from rich.table import Table
from rich.markup import escape
from rich.tree import Tree
from curvtools.cli.curvcfg.lib.globals.curvpaths import get_curv_paths
from pathlib import Path
from curvtools.cli.curvcfg.lib.globals.console import console
from curvtools.cli.curvcfg.lib.globals.types import CurvCliArgs
import click

def get_box(use_ascii_box: bool = False) -> Box:
    return ASCII2 if use_ascii_box else ROUNDED

###############################################################################
#
# Display tree of TOML files helper
#
###############################################################################

def display_toml_tree(tomls_list: list[str], use_ascii_box: bool = False, verbosity: int = 0) -> None:
    """
    Display the tree of TOML files.
    
    Args:
        tomls_list: the list of TOML files

    Returns:
        None
    """
    # Display tree of TOML files
    rel_base_path = get_curv_paths().mk_rel_to_curv_root(tomls_list[0])
    if verbosity >= 1:
        if len(tomls_list) > 1:
            tree = Tree(f"[bold cyan]TOML Configuration Tree[/bold cyan]")
            tree.add(f"[bold green]Base:[/bold green] [bold]{Path(rel_base_path).stem}[/bold] {escape('[' + rel_base_path + ']')}")
            overlays_branch = tree.add("[bold yellow]Overlays (later take precedence):[/bold yellow]")
            for i, overlay_path in enumerate(tomls_list[1:], 1):
                rel_overlay_path = get_curv_paths().mk_rel_to_curv_root(overlay_path)
                overlays_branch.add(f"[dim]{i}.[/dim] {rel_overlay_path}")
        else:
            tree = Tree(f"[bold cyan]Base:[/bold cyan] [bold]{Path(rel_base_path).stem}[/bold] {escape('[' + rel_base_path + ']')}")
        console.print(Panel(tree, 
            expand=False, 
            title=f"[bold green]Configuration[/bold green]", 
            border_style="cyan",
            box=get_box(use_ascii_box),
            ))
        console.print()  # spacing


###############################################################################
#
# Display merged TOML table helper
#
###############################################################################

def display_merged_toml_table(config_values: CfgValues, target_path: str, use_ascii_box: bool = False, verbosity: int = 0) -> None:
    """
    Display the merged TOML table.
    
    Args:
        config_values: the config values
        target_path: the target path
        verbosity: the verbosity level

    Returns:
        None
    """
    if verbosity >= 1:
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

        # p = Panel(f"{target_path}", 
        #     style="green bold", 
        #     border_style="white", 
        #     expand=True,
        #     box=get_box(use_ascii_box),
        #     padding=(1, 2, 1, 2))
        # console.print(p)

        table_options = {}
        # table_options["title"] = f"{target_path}"
        # table_options["title_style"] = Style(color="green", bold=True)
        table_options["box"] = get_box(use_ascii_box)
        table_options["caption"] = f"config hash: {config_values.hash()}"

        if verbosity >= 2:
            table = Table(expand=False, **table_options)
            table.add_column(f"Variable [dim](source: [green]{target_path}[/green])[/dim]", overflow="fold")
            table.add_column("Value", overflow="fold")
            table.add_column("Type", overflow="fold")
            table.add_column("Constraints", overflow="fold")
            table.add_column("Locations", overflow="fold")
            for k in sorted(config_values.keys()):
                if not k.startswith("CFG_"):
                    continue
                v = config_values[k]
                table.add_row(
                    f"{colorize_key(k)}\n{v.meta.toml_path}",
                    f"{colorize_value(v.meta.makefile_type, str(v))}",
                    colorize_value(v.schema_meta.get_type_str()[0], v.schema_meta.get_type_str()[0]),
                    colorize_value(v.schema_meta.get_type_str()[1], v.schema_meta.get_type_str()[1]),
                    v.locations_str(),
                )
        else:
            table = Table(expand=False, **table_options)
            table.add_column(f"Variable [dim](source: [green]{target_path}[/green])[/dim]", overflow="fold")
            table.add_column("Value", overflow="fold")
            for k in sorted(config_values.keys()):
                if not k.startswith("CFG_"):
                    continue
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

def display_dep_file_contents(contents: str, target_path: str, use_ascii_box: bool = False) -> None:
    """
    Display the dep file contents.
    
    Args:
        contents: the contents of the dep file
        target_path: the target path
        use_ascii_box: whether to use ascii box

    Returns:
        None
    """
    title = get_curv_paths().mk_rel_to_cwd(target_path)
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

def display_curvcfg_settings_table(ctx: click.Context, use_ascii_box: bool = False):
    # print the tool's config settings
    curvcfg_settings_path = ctx.obj.get('curvcfg_settings_path', None)
    curvcfg_settings = ctx.obj.get('curvcfg_settings', None)
    if curvcfg_settings is not None:
        if curvcfg_settings_path is not None:
            title: Optional[TextType]= f"[blue]from file: [bold]{curvcfg_settings_path}[/bold][/blue]"
        else:
            title: Optional[TextType]= None
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

def display_args_table(args: CurvCliArgs, title: str, use_ascii_box: bool = False):
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
        if isinstance(value, list):
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
