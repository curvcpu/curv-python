from __future__ import annotations

from functools import partial
from typing import Union

from rich.box import SIMPLE
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    RenderableColumn
)
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.table import Column

from .display_options import DisplayOptions, SizeOpt, SizeOptCustom, StackupOpt

__all__ = ["StackedProgressTable"]


def _resolve_style(style: Style | str | None) -> Style | None:
    if style is None:
        return None
    if isinstance(style, Style):
        return style
    return Style.parse(style)


class StackedProgressTable:
    """Utility that lays out worker and overall progress bars in a Rich table."""

    def __init__(self, display_options: DisplayOptions | None = None) -> None:
        self.display_options = display_options or DisplayOptions()

        self.is_full_screen = True if self.display_options.Size == SizeOpt.FULL_SCREEN else False
        self.expand = True if self.display_options.Size == SizeOpt.FULL_SCREEN else False
        self.transient = self.display_options.Transient

        job_bar_args, overall_bar_args = self._make_bar_args(
            self.display_options.Size,
            self.display_options.WorkerBarColors, 
            self.display_options.OverallBarColors)

        job_progress_columns = self._make_job_progress_columns(
            finished_text="[bold green]:heavy_check_mark:[/bold green]", 
            job_bar_args=job_bar_args)
        self.job_progress = Progress(
            *job_progress_columns, expand=self.expand, transient=self.transient
        )

        overall_progress_columns = self._make_overall_progress_columns(
            finished_text="[bold green]:heavy_check_mark:[/bold green]", 
            overall_bar_args=overall_bar_args)
        self.overall_progress = Progress(
            *overall_progress_columns, expand=self.expand, transient=self.transient
        )

        self.progress_table = self._build_progress_table()

    def _make_job_progress_columns(self, finished_text: str, job_bar_args: dict[str, object]) -> list[ProgressColumn]:
        job_progress_columns: list[ProgressColumn] = [
            # RenderableColumn(
            #     Text("[dim]{task.description}[/dim]"),
            #     table_column=Column(overflow="fold", width=self.display_options.MaxNamesLength),
            # ),
            TextColumn("{task.description}", style="gray66"),
            SpinnerColumn(finished_text=finished_text),
            BarColumn(
                bar_width=job_bar_args["width"],
                **self.display_options.WorkerBarColors.remap_bar_style_names(),
            ),
            TextColumn("{task.percentage:>5.1f}%", style="gray66"),
        ]
        if job_bar_args.get("fn_remaining") is not None:
            job_progress_columns.append(job_bar_args["fn_remaining"]())
        return job_progress_columns

    def _make_overall_progress_columns(self, finished_text: str, overall_bar_args: dict[str, object]) -> list[ProgressColumn]:
        overall_style = _resolve_style(self.display_options.OverallNameStrStyle) or Style()
        overall_bar_styles = self.display_options.OverallBarColors.remap_bar_style_names()
        # HACK:  they can specify a negative number here to prevent truncation and instead 
        # flow to 2 lines; this should really be two separate fields...
        tc = Column(overflow="fold", width=abs(self.display_options.MaxNamesLength)) if self.display_options.MaxNamesLength is not None and self.display_options.MaxNamesLength < 0 else None
        overall_progress_columns: list[ProgressColumn] = [
            TextColumn("{task.description}", style=overall_style, table_column=tc),
            # TextColumn("{task.description}", style=overall_style),
            SpinnerColumn(finished_text="[bold green]:heavy_check_mark:[/bold green]"),
            BarColumn(
                bar_width=overall_bar_args["width"],
                **overall_bar_styles,
            ),
            TextColumn("{task.percentage:>5.1f}%", style="gray66"),
        ]
        if overall_bar_args.get("fn_elapsed") is not None:
            overall_progress_columns.append(overall_bar_args["fn_elapsed"]())
        if overall_bar_args.get("fn_remaining") is not None:
            overall_progress_columns.append(overall_bar_args["fn_remaining"]())
        return overall_progress_columns
    
    def _make_bar_args(self, size: Union[SizeOpt, SizeOptCustom], worker_bar_colors: BarColors, overall_bar_colors: BarColors) -> tuple[dict[str, object], dict[str, object]]:
        job_bar_args: dict[str, object] = worker_bar_colors.get_args_dict()
        overall_bar_args: dict[str, object] = overall_bar_colors.get_args_dict()
        match size:
            case SizeOpt.SMALL:
                job_bar_args.update({"width": 20, "fn_remaining": None})
                overall_bar_args.update(
                    {
                        "width": 13,
                        "fn_elapsed": None,
                        "fn_remaining": partial(
                            TimeRemainingColumn,
                            compact=False,
                            elapsed_when_finished=True,
                        ),
                    }
                )
            case SizeOpt.MEDIUM:
                job_bar_args.update({"width": 40, "fn_remaining": None})
                overall_bar_args.update(
                    {
                        "width": 33,
                        "fn_elapsed": None,
                        "fn_remaining": partial(
                            TimeRemainingColumn,
                            compact=False,
                            elapsed_when_finished=True,
                        ),
                    }
                )
            case SizeOpt.LARGE:
                job_bar_args.update({"width": 80, "fn_remaining": None})
                overall_bar_args.update(
                    {
                        "width": 75,
                        "fn_elapsed": None,
                        "fn_remaining": partial(
                            TimeRemainingColumn,
                            compact=False,
                            elapsed_when_finished=True,
                        ),
                    }
                )
            case SizeOpt.FULL_SCREEN:
                job_bar_args.update(
                    {
                        "width": None,
                        "fn_remaining": partial(
                            TimeRemainingColumn,
                            compact=False,
                            elapsed_when_finished=True,
                        ),
                    }
                )
                overall_bar_args.update(
                    {
                        "width": None,
                        "fn_elapsed": None,
                        "fn_remaining": partial(
                            TimeRemainingColumn,
                            compact=False,
                            elapsed_when_finished=True,
                        ),
                    }
                )
            case SizeOptCustom(job_bar_args=job_bar_args, overall_bar_args=overall_bar_args) as size_opt_custom:
                job_bar_args.update(**size_opt_custom.job_bar_args)
                overall_bar_args.update(**size_opt_custom.overall_bar_args)
            case _:
                raise ValueError(f"Invalid size option: {self.display_options.Size!r}")
        return job_bar_args, overall_bar_args

    def update_bar_colors(self, bar_colors: BarColors, worker_bar_colors: BarColors) -> None:
        self.display_options.OverallBarColors = bar_colors
        self.display_options.WorkerBarColors = worker_bar_colors

        job_bar_args, overall_bar_args = self._make_bar_args(
            self.display_options.Size,
            self.display_options.WorkerBarColors, 
            self.display_options.OverallBarColors)

        job_progress_columns = self._make_job_progress_columns(
            finished_text="[bold green]:heavy_check_mark:[/bold green]", 
            job_bar_args=job_bar_args)
        self.job_progress.columns = job_progress_columns

        overall_progress_columns = self._make_overall_progress_columns(
            finished_text="[bold green]:heavy_check_mark:[/bold green]", 
            overall_bar_args=overall_bar_args)
        self.overall_progress.columns = overall_progress_columns

        # self.progress_table = self._build_progress_table()

    def update_message(self, message: MessageLineOpt) -> None:
        self.display_options.Message = message
        self.progress_table = self._build_progress_table()

    def update_bounding_rect(self, bounding_rect: BoundingRectOpt) -> None:
        self.display_options.BoundingRect = bounding_rect
        self.progress_table = self._build_progress_table()

    def get_job_progress(self) -> Progress:
        return self.job_progress

    def get_overall_progress(self) -> Progress:
        return self.overall_progress

    def get_progress_table(self) -> Table:
        self.progress_table = self._build_progress_table()
        return self.progress_table

    def _build_progress_table(self) -> Table:
        inner_table_args: dict[str, object] = {}
        column_args: dict[str, object] = {"justify": "center"}
        footer_args: dict[str, object] = {}

        stackup = self.display_options.Stackup
        show_workers = stackup not in {
            StackupOpt.OVERALL,
            StackupOpt.OVERALL_MESSAGE,
            StackupOpt.MESSAGE_OVERALL,
        }

        if stackup == StackupOpt.OVERALL:
            inner_table_args.update({"show_header": True, "show_footer": False})
            column_args["header"] = self.overall_progress
        elif stackup == StackupOpt.OVERALL_WORKERS:
            inner_table_args.update({"show_header": True, "show_footer": False})
            column_args["header"] = self.overall_progress
        elif stackup == StackupOpt.WORKERS_OVERALL:
            inner_table_args.update({"show_header": False, "show_footer": True})
            footer_args["footer"] = self.overall_progress
        elif stackup in {StackupOpt.OVERALL_WORKERS_MESSAGE, StackupOpt.OVERALL_MESSAGE}:
            inner_table_args["show_header"] = True
            column_args["header"] = self.overall_progress
            if not self.display_options.Message.is_unused():
                inner_table_args["show_footer"] = True
                footer_table = Table.grid(expand=False)
                footer_table.add_column(justify="center")
                footer_table.add_row(Align(Text(self.display_options.Message.message, style=self.display_options.Message.resolved_style()), align="center"))
                footer_args["footer"] = Align(footer_table, align="center")
                # footer_args["footer_style"] = self.display_options.Message.resolved_style()
            else:
                inner_table_args["show_footer"] = False
        elif stackup in {StackupOpt.MESSAGE_WORKERS_OVERALL, StackupOpt.MESSAGE_OVERALL}:
            inner_table_args["show_footer"] = True
            footer_args["footer"] = self.overall_progress
            footer_args["footer_style"] = Style(color="bright_white")
            if not self.display_options.Message.is_unused():
                inner_table_args["show_header"] = True
                header_table = Table.grid(expand=False)
                header_table.add_column(justify="center")
                header_table.add_row(Align(Text(self.display_options.Message.message, style=self.display_options.Message.resolved_style()), align="center"))
                column_args["header"] = Align(header_table, align="center")
                # column_args["header_style"] = self.display_options.Message.resolved_style()
            else:
                inner_table_args["show_header"] = False
        else:
            raise ValueError(f"Unhandled stackup option: {stackup!r}")

        progress_table = Table.grid(expand=self.expand)

        if self.display_options.BoundingRect.is_visible():
            bordered_table = Table(
                box=SIMPLE,
                expand=self.expand,
                **inner_table_args,
                style=self.display_options.BoundingRect.get_args_dict()["border_style"],
            )
            if inner_table_args.get("show_header"):
                column_args["header_style"] = column_args.get("header_style")
            if inner_table_args.get("show_footer"):
                column_args["footer"] = footer_args.get("footer")
                column_args["footer_style"] = footer_args.get("footer_style")
            bordered_table.add_column(**column_args)
            if show_workers:
                bordered_table.add_row(self.job_progress)
            panel = Panel.fit(
                bordered_table,
                **self.display_options.BoundingRect.get_args_dict(),
            )
            progress_table.add_row(panel)
        else:
            inner_table = Table.grid(expand=self.expand)
            inner_table.add_column(**column_args)
            if inner_table_args.get("show_header"):
                inner_table.add_row(
                    Align(column_args.get("header", ""), align="center"),
                    style=column_args.get("header_style"),
                )
            if show_workers:
                inner_table.add_row(self.job_progress)
            if inner_table_args.get("show_footer"):
                inner_table.add_row(
                    Align(footer_args.get("footer", ""), align="center"),
                    style=footer_args.get("footer_style"),
                )
            progress_table.add_row(inner_table)

        return progress_table

