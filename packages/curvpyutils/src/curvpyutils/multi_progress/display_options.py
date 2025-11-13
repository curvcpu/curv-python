from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Optional, Union
from functools import partial
from rich.progress import ProgressColumn, TimeRemainingColumn

from rich.style import Style

__all__ = [
    "BarColors",
    "BoundingRectOpt",
    "DisplayOptions",
    "MessageLineOpt",
    "SizeOpt",
    "SizeOptCustom",
    "StackupOpt",
    "Style",
    "get_default_display_options",
]


def _resolve_style(style: Style | str | None) -> Style:
    if style is None:
        return Style()
    if isinstance(style, Style):
        return style
    return Style.parse(style)


class StackupOpt(Enum):
    OVERALL = auto()
    OVERALL_WORKERS = auto()
    WORKERS_OVERALL = auto()
    OVERALL_WORKERS_MESSAGE = auto()
    MESSAGE_WORKERS_OVERALL = auto()
    OVERALL_MESSAGE = auto()
    MESSAGE_OVERALL = auto()


class SizeOpt(Enum):
    SMALL = auto()
    MEDIUM = auto()
    LARGE = auto()
    FULL_SCREEN = auto()

class SizeOptCustom:
    class BarArgs(dict[str, object]):
        width: int = field(default=20)
        fn_elapsed: Callable[[], ProgressColumn] = field(default=None)
        fn_remaining: Callable[[], ProgressColumn] = field(default=None)
        def __init__(
            self, 
            width: int, 
            fn_elapsed: Callable[[], ProgressColumn] | None = None, 
            fn_remaining: Callable[[], ProgressColumn] | None = partial(
                TimeRemainingColumn,
                compact=False,
                elapsed_when_finished=True,
        )) -> None:
            self["width"] = width
            self["fn_elapsed"] = fn_elapsed
            self["fn_remaining"] = fn_remaining
            super().__init__()
        def get_args_dict(self) -> dict[str, object]:
            return {
                "width": self["width"],
                "fn_elapsed": self["fn_elapsed"],
                "fn_remaining": self["fn_remaining"],
            }
    def __init__(self, job_bar_args: "SizeOptCustom.BarArgs", overall_bar_args: "SizeOptCustom.BarArgs", max_names_length: int | None = None):
        self.job_bar_args = job_bar_args
        self.overall_bar_args = overall_bar_args
        self.max_names_length = max_names_length

@dataclass(slots=True)
class BarColors:
    completed: Style | str | None = None
    finished: Style | str | None = None
    text: Style | str | None = None

    def _styles(self) -> dict[str, Style]:
        return {
            "completed": _resolve_style(self.completed) if self.completed is not None else None,
            "finished": _resolve_style(self.finished) if self.finished is not None else None,
            "text": _resolve_style(self.text) if self.text is not None else None,
        }

    def get_args_dict(self) -> dict[str, Style | None]:
        styles = self._styles()
        return {k: v for k, v in styles.items() if v is not None}

    def remap_bar_style_names(self) -> dict[str, Style]:
        mapping = {
            "completed": "complete_style",
            "finished": "finished_style",
            "text": "style",
        }
        return {
            mapping[name]: style
            for name, style in self._styles().items()
            if style is not None and name in mapping
        }

    @classmethod
    def default(cls) -> BarColors:
        return cls()

    @classmethod
    def green_white(cls) -> BarColors:
        return cls(
            completed=Style(color="green", bold=True),
            finished=Style(color="green", bold=True),
            text=Style(color="white", bold=False),
        )

    @classmethod
    def red(cls) -> BarColors:
        return cls(
            completed=Style(color="bright_red", bold=True),
            finished=Style(color="bright_red", bold=True),
            text=Style(color="red", bold=True),
        )

@dataclass(slots=True)
class MessageLineOpt:
    message: Optional[str] = None
    message_style: Style | str | None = None

    def is_unused(self) -> bool:
        return self.message is None

    def resolved_style(self) -> Style:
        return _resolve_style(self.message_style)


@dataclass(slots=True)
class BoundingRectOpt:
    title: Optional[str] = None
    border_style: Style | str | None = None

    def is_visible(self) -> bool:
        return self.title is not None or self.border_style is not None

    def get_args_dict(self) -> dict[str, Style | str]:
        return {
            "title": self.title or "",
            "border_style": _resolve_style(self.border_style),
        }


@dataclass(slots=True)
class DisplayOptions:
    BoundingRect: BoundingRectOpt = field(default_factory=BoundingRectOpt)
    Stackup: StackupOpt = StackupOpt.OVERALL_WORKERS_MESSAGE
    Message: MessageLineOpt = field(default_factory=MessageLineOpt)
    Size: Union[SizeOpt, SizeOptCustom] = SizeOpt.MEDIUM
    Transient: bool = False
    OverallBarColors: BarColors = field(default_factory=BarColors.default)
    WorkerBarColors: BarColors = field(default_factory=BarColors.default)
    OverallNameStr: str = "Overall"
    OverallNameStrStyle: Style | str = field(
        default_factory=lambda: Style(color="white", bold=True)
    )
    FnWorkerIdToName: Callable[[int], str] = field(
        default_factory=lambda: (lambda worker_id: f"Worker {worker_id}")
    )
    MaxNamesLength: int | None = field(default=None)

    def __post_init__(self) -> None:
        if isinstance(self.OverallNameStrStyle, str):
            self.OverallNameStrStyle = Style.parse(self.OverallNameStrStyle)
        match self.Size:
            case SizeOpt.SMALL:
                self.MaxNamesLength = 10
            case SizeOpt.MEDIUM:
                self.MaxNamesLength = 20
            case SizeOpt.LARGE:
                self.MaxNamesLength = 40
            case SizeOpt.FULL_SCREEN:
                self.MaxNamesLength = None
            # HACK:  they can specify a negative number here to prevent truncation and
            # instead flow to 2 lines; this should really be two separate fields...
            case SizeOptCustom(max_names_length=max_names_length) as size_opt_custom:
                self.MaxNamesLength = size_opt_custom.max_names_length
            case _:
                self.MaxNamesLength = None


def get_default_display_options(
    msg: Optional[str] = None, *, transient: bool = False
) -> DisplayOptions:
    return DisplayOptions(
        Message=MessageLineOpt(message=msg),
        Transient=transient,
    )

