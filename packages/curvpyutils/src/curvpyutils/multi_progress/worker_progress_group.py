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
    def create(cls, job_progress: Progress, worker_id: int) -> _WorkerProgress:
        task_id = job_progress.add_task(f"Worker {worker_id}", total=100.0)
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
        self.workers: Dict[int, _WorkerProgress] = {}
        self.overall_task_id: TaskID | None = None

    def add_worker(self, worker_id: int) -> None:
        if worker_id in self.workers:
            return
        worker = _WorkerProgress.create(
            self.stacked_progress_table.get_job_progress(), worker_id
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
            self.display_options.OverallNameStr, total=100.0
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
            self.stacked_progress_table.get_progress_table(),
            refresh_per_second=10,
            transient=self.stacked_progress_table.transient,
            screen=self.is_full_screen,
            console=console,
        )

