from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from rich.live import Live
from rich.progress import Progress, TaskID
from rich.console import Console

from .display_options import DisplayOptions
from .stacked_progress_table import StackedProgressTable

__all__ = ["WorkerProgressGroup"]


@dataclass(slots=True)
class _WorkerProgress:
    job_progress: Progress
    worker_id: int
    task_id: TaskID

    @classmethod
    def create(cls, job_progress: Progress, worker_id: int, fn_worker_id_to_name: Callable[[int], str]) -> _WorkerProgress:
        task_id = job_progress.add_task(description=fn_worker_id_to_name(worker_id), total=100.0)
        return cls(job_progress=job_progress, worker_id=worker_id, task_id=task_id)

    def completed_pct(self) -> float:
        completed = self.job_progress.tasks[self.task_id].completed
        if completed is None:
            return 0.0
        return min(max(completed, 0.0), 100.0)

class WorkerProgressGroup:
    """Manage a set of Rich progress bars for worker tasks plus an overall bar."""

    def __init__(self, display_options: DisplayOptions | None = None) -> None:
        self.display_options = display_options or DisplayOptions()
        self.stacked_progress_table = StackedProgressTable(
            display_options=self.display_options
        )
        self.is_full_screen = self.stacked_progress_table.is_full_screen
        self.max_names_length: int | None = self.display_options.MaxNamesLength

        # worker tasks and overall task
        self.workers: Dict[int, _WorkerProgress] = {}
        self.overall_task_id: TaskID | None = None

    def update_display_options(self, new_display_options: DisplayOptions) -> None:
        """
        Only supports updating the following display options:
        - OverallBarColors
        - WorkerBarColors
        - Message
        - BoundingRect
        Rest of new_display_options is ignored.
        """
        overall_bar_colors_changed = self.display_options.OverallBarColors != new_display_options.OverallBarColors
        worker_bar_colors_changed = self.display_options.WorkerBarColors != new_display_options.WorkerBarColors
        message_changed = self.display_options.Message != new_display_options.Message
        bounding_rect_changed = self.display_options.BoundingRect != new_display_options.BoundingRect
        if overall_bar_colors_changed or worker_bar_colors_changed:
            self.display_options.OverallBarColors = new_display_options.OverallBarColors
            self.display_options.WorkerBarColors = new_display_options.WorkerBarColors
            self.stacked_progress_table.update_bar_colors(bar_colors=self.display_options.OverallBarColors, worker_bar_colors=self.display_options.WorkerBarColors)
        if message_changed:
            self.display_options.Message = new_display_options.Message
            self.stacked_progress_table.update_message(message=self.display_options.Message)
        if bounding_rect_changed:
            self.display_options.BoundingRect = new_display_options.BoundingRect
            self.stacked_progress_table.update_bounding_rect(bounding_rect=self.display_options.BoundingRect)

    def truncate_description_str(self, description: str|Callable[[int], str]) -> str|Callable[[int], str]:
        if self.max_names_length is None or self.max_names_length < 0:
            return description
        if isinstance(description, str):
            return description[:self.max_names_length] if len(description) <= self.max_names_length else description[:self.max_names_length-1] + "…"
        else:
            return lambda worker_id: description(worker_id)[:self.max_names_length] if len(description(worker_id)) <= self.max_names_length else description(worker_id)[:self.max_names_length-1] + "…"

    def add_worker(self, worker_id: int) -> None:
        if worker_id in self.workers:
            return
        worker = _WorkerProgress.create(
            self.stacked_progress_table.get_job_progress(), 
            worker_id, 
            self.truncate_description_str(self.display_options.FnWorkerIdToName)
        )
        self.workers[worker_id] = worker

    def remove_worker(self, worker_id: int) -> None:
        worker = self.workers.pop(worker_id, None)
        if worker is None:
            return
        job_progress = self.stacked_progress_table.get_job_progress()
        job_progress.remove_task(worker.task_id)

    def remove_all(self) -> None:
        for worker_id in list(self.workers.keys()):
            self.remove_worker(worker_id)

    def _ensure_overall_task(self) -> None:
        overall_progress = self.stacked_progress_table.get_overall_progress()
        if self.overall_task_id is not None:
            overall_progress.remove_task(self.overall_task_id)
        self.overall_task_id = overall_progress.add_task(
            self.truncate_description_str(self.display_options.OverallNameStr), total=100.0
        )

    def _overall_completed_pct(self) -> float:
        if not self.workers:
            return 0.0
        return sum(worker.completed_pct() for worker in self.workers.values()) / len(
            self.workers
        )

    def update_all(self, latest: Dict[int, float] | None, *, is_advance: bool = False) -> None:
        if latest:
            job_progress = self.stacked_progress_table.get_job_progress()
            for worker_id, delta in latest.items():
                worker = self.workers.get(worker_id)
                if worker is None:
                    continue
                if is_advance:
                    job_progress.advance(worker.task_id, advance=max(0.0, min(100.0, delta)))
                else:
                    job_progress.update(
                        worker.task_id, completed=max(0.0, min(100.0, delta))
                    )
            if is_advance:
                for worker_id in latest:
                    worker = self.workers.get(worker_id)
                    if worker is None:
                        continue
                    job_progress.update(
                        worker.task_id,
                        completed=max(0.0, min(100.0, worker.completed_pct())),
                    )

        if self.overall_task_id is None:
            self._ensure_overall_task()
        overall_progress = self.stacked_progress_table.get_overall_progress()
        overall_progress.update(
            self.overall_task_id, completed=self._overall_completed_pct()
        )

    def complete_all(self) -> None:
        self.update_all({worker_id: 100.0 for worker_id in self.workers})

    def is_finished(self) -> bool:
        return all(worker.completed_pct() >= 100.0 for worker in self.workers.values())

    def with_live(self, *, console: Optional[Console] = None) -> Live:
        return Live(
            #self.stacked_progress_table.get_progress_table(),
            refresh_per_second=4,
            transient=self.stacked_progress_table.transient,
            screen=self.is_full_screen,
            console=console,
            auto_refresh=True,
            get_renderable=self.stacked_progress_table.get_progress_table,
        )

