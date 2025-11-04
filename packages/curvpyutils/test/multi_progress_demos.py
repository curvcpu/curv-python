#!/usr/bin/env python3
"""Demonstrations for the `curvpyutils.multi_progress` helpers.

Run interactively (default) to see Rich-rendered progress bars, or pass
``--snapshot`` to capture the rendered bars for regression testing, e.g.:

    python multi_progress_demos.py --seed 123 --snapshot --width 90

The ``--seed`` option guarantees deterministic behaviour for automated checks.
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import io
import random
import sys
from time import sleep
from typing import Iterable, List, Optional

from rich.console import Console
from rich.style import Style

from curvpyutils.multi_progress.display_options import (
    BarColors,
    BoundingRectOpt,
    DisplayOptions,
    MessageLineOpt,
    SizeOpt,
    StackupOpt,
)
from curvpyutils.multi_progress.worker_progress_group import WorkerProgressGroup


def _run_worker_group(
    worker_group: WorkerProgressGroup,
    rng: random.Random,
    *,
    use_live: bool,
    step_delay: float,
    console: Optional[Console] = None,
) -> int:
    """Drive the worker group to completion and return iteration count."""

    latest = {worker_id: 0.0 for worker_id in worker_group.workers.keys()}
    iterations = 0
    context = worker_group.with_live(console=console) if use_live else nullcontext()

    with context:
        while not worker_group.is_finished():
            if step_delay:
                sleep(step_delay)
            for worker_id in latest:
                latest[worker_id] = min(100.0, latest[worker_id] + rng.randint(1, 5))
            worker_group.update_all(latest=latest)
            iterations += 1

        worker_group.complete_all()
        if step_delay:
            sleep(step_delay)

    return iterations


def _format_worker_completions(worker_group: WorkerProgressGroup) -> List[float]:
    return [worker.completed_pct() for worker in worker_group.workers.values()]


def _summarize(
    name: str,
    worker_group: WorkerProgressGroup,
    iterations: int,
) -> str:
    completions = _format_worker_completions(worker_group)
    overall = sum(completions) / len(completions) if completions else 0.0
    worker_totals = ", ".join(f"{pct:.1f}" for pct in completions)
    summary = (
        f"{name}: workers={len(worker_group.workers)} "
        f"iterations={iterations} "
        f"overall={overall:.1f} "
        f"worker_totals=[{worker_totals}] "
        f"transient={worker_group.display_options.Transient}"
    )
    message_text = worker_group.display_options.Message.message
    if message_text:
        summary += f" message={message_text!r}"
    return summary


def demo1(
    rng: random.Random,
    *,
    use_live: bool,
    step_delay: float,
    capture: bool,
    width: int,
) -> str:
    display_options = DisplayOptions(
        BoundingRect=BoundingRectOpt("This is title", "green"),
        Stackup=StackupOpt.OVERALL_WORKERS_MESSAGE,
        Size=SizeOpt.SMALL,
        OverallBarColors=BarColors.green_white(),
        WorkerBarColors=BarColors.green_white(),
        OverallNameStr="Overall",
        OverallNameStrStyle=Style(color="white", bold=True),
        Message=MessageLineOpt("This is message line", Style(color="white", bold=True)),
        Transient=False,
    )
    worker_group = WorkerProgressGroup(display_options=display_options)
    for worker_id in range(3):
        worker_group.add_worker(worker_id)
    live_console = (
        Console(
            file=io.StringIO(),
            force_terminal=True,
            width=width,
            color_system=None,
        )
        if capture
        else None
    )
    iterations = _run_worker_group(
        worker_group,
        rng,
        use_live=use_live,
        step_delay=step_delay,
        console=live_console,
    )
    summary = _summarize("demo1", worker_group, iterations)
    if live_console is not None:
        snapshot_console = Console(
            force_terminal=True,
            width=width,
            color_system=None,
        )
        with snapshot_console.capture() as capture:
            snapshot_console.print(worker_group.stacked_progress_table.get_progress_table())
        rendered = capture.get().rstrip("\n")
        return f"{rendered}\n{summary}" if rendered else summary
    return summary


def demo2(
    rng: random.Random,
    *,
    use_live: bool,
    step_delay: float,
    capture: bool,
    width: int,
) -> str:
    worker_group = WorkerProgressGroup()
    for worker_id in range(3):
        worker_group.add_worker(worker_id)
    live_console = (
        Console(
            file=io.StringIO(),
            force_terminal=True,
            width=width,
            color_system=None,
        )
        if capture
        else None
    )
    iterations = _run_worker_group(
        worker_group,
        rng,
        use_live=use_live,
        step_delay=step_delay,
        console=live_console,
    )
    summary = _summarize("demo2", worker_group, iterations)
    if live_console is not None:
        snapshot_console = Console(
            force_terminal=True,
            width=width,
            color_system=None,
        )
        with snapshot_console.capture() as capture:
            snapshot_console.print(worker_group.stacked_progress_table.get_progress_table())
        rendered = capture.get().rstrip("\n")
        return f"{rendered}\n{summary}" if rendered else summary
    return summary


def demo3(
    rng: random.Random,
    *,
    use_live: bool,
    step_delay: float,
    capture: bool,
    width: int,
) -> str:
    display_options = DisplayOptions(
        Transient=True,
        Message=MessageLineOpt("Disappearing...", Style(color="white", bold=True)),
    )
    worker_group = WorkerProgressGroup(display_options=display_options)
    for worker_id in range(5):
        worker_group.add_worker(worker_id)
    live_console = (
        Console(
            file=io.StringIO(),
            force_terminal=True,
            width=width,
            color_system=None,
        )
        if capture
        else None
    )
    iterations = _run_worker_group(
        worker_group,
        rng,
        use_live=use_live,
        step_delay=step_delay,
        console=live_console,
    )
    summary = _summarize("demo3", worker_group, iterations)
    if live_console is not None:
        snapshot_console = Console(
            force_terminal=True,
            width=width,
            color_system=None,
        )
        with snapshot_console.capture() as capture:
            snapshot_console.print(worker_group.stacked_progress_table.get_progress_table())
        rendered = capture.get().rstrip("\n")
        return f"{rendered}\n{summary}" if rendered else summary
    return summary


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed for deterministic random behaviour.",
    )
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Capture progress-bar renders for snapshot testing.",
    )
    parser.add_argument(
        "--step-delay",
        type=float,
        default=None,
        help="Override sleep duration between updates (seconds).",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=80,
        help="Console width to use when capturing snapshots.",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    stdout_is_tty = sys.stdout.isatty()
    capture = args.snapshot or not stdout_is_tty
    use_live = True if capture else stdout_is_tty
    if not use_live and not capture:
        use_live = True
    step_delay = (
        args.step_delay
        if args.step_delay is not None
        else (0.0 if capture else 0.1)
    )

    outputs = [
        demo1(rng, use_live=use_live, step_delay=step_delay, capture=capture, width=args.width),
        demo2(rng, use_live=use_live, step_delay=step_delay, capture=capture, width=args.width),
        demo3(rng, use_live=use_live, step_delay=step_delay, capture=capture, width=args.width),
    ]

    for index, output in enumerate(outputs):
        if capture:
            sys.stdout.write(output.rstrip("\n"))
            sys.stdout.write("\n")
            if index != len(outputs) - 1:
                sys.stdout.write("\n")
        else:
            print(output)
            print()
            if index != len(outputs) - 1:
                print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

