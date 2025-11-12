from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Optional

from rich.style import Style

__all__ = [
    "BarColors",
    "BoundingRectOpt",
    "DisplayOptions",
    "MessageLineOpt",
    "SizeOpt",
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
    Size: SizeOpt = SizeOpt.MEDIUM
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


def get_default_display_options(
    msg: Optional[str] = None, *, transient: bool = False
) -> DisplayOptions:
    return DisplayOptions(
        Message=MessageLineOpt(message=msg),
        Transient=transient,
    )

