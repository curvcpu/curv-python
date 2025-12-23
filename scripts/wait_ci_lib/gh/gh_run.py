#!/usr/bin/env -S uv run --script --all-packages

"""
This module provides a class for constructing GhRun and GhJob objects from GitHub 
Actions run and jobs JSON, and for updating the GhRun object with new GhJob objects.
"""

from enum import Enum, auto
import subprocess
import sys
import time
from datetime import datetime, timezone
from dataclasses import field, dataclass
from typing import Any, Callable
from collections.abc import Generator
from .gh_api import GhApiFetcher
from rich.console import Console
from rich.text import Text
from rich.style import Style
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.traceback import install, Traceback
import argparse
import os
import itertools
from curvpyutils.test_helpers import compare_files
import pytest
from .gh_api_parallel import GhPollingClient
from .github_actions_current_state import GithubActionsCurrentState

console = Console()

# default poll intervals in seconds to avoid hitting API too often
DEFAULT_INTERVALS = {
    'RUN_POLL':  2,
    'JOBS_POLL': 2,
}
# how long to wait before timing out
TIMEOUT_ATTEMPTS = {
    # timeout if we make 2 minutes worth of attempts
    'RUN_POLL':  (60*2) // DEFAULT_INTERVALS['RUN_POLL'],
    # timeout if we make 10 minutes worth of attempts
    'JOBS_POLL': (60*10) // DEFAULT_INTERVALS['JOBS_POLL'],
}

class GhStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    QUEUED = "queued"
    OTHER = "(other)"

LONGEST_STATUS_NAME_LEN = max(len(status.value) for status in GhStatus)

class GhConclusion(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    NULL = None

LONGEST_CONCLUSION_NAME_LEN = max(len(conclusion.value) if conclusion.value else 0 for conclusion in GhConclusion)

class GhJobStep:
    def __init__(self, name: str, status: GhStatus, conclusion: GhConclusion = GhConclusion.NULL):
        self.name = name
        self.status = status
        self.conclusion = conclusion
    def __eq__(self, other: object) -> bool:
        """
        Equality function for GhJobStep objects.
        """
        if not isinstance(other, GhJobStep):
            return NotImplemented
        return (
            self.name == other.name and
            self.status == other.status and
            self.conclusion == other.conclusion
        )
    def __hash__(self) -> int:
        """
        Hash function for GhJobStep object so they can be used as keys in dictionaries or sets.
        """
        return hash((self.name, self.status, self.conclusion))

@dataclass
class ProgressStats:
    cnt_complete: int = field(compare=True, default=0)
    cnt_in_progress: int = field(compare=True, default=0)
    cnt_total: int = field(compare=True, default=0)
    @property
    def completed(self) -> int:
        # scoring function is: cnt_complete + (cnt_in_progress * 0.5)
        return self.cnt_complete + (self.cnt_in_progress * 0.5)
    @property
    def total(self) -> int:
        return self.cnt_total
    @property
    def percent_complete(self) -> float:
        return self.completed / self.total * 100.0 if self.total > 0 else 0.0
    def __eq__(self, other: object) -> bool:
        """
        Equality function for ProgressStats objects.
        """
        if not isinstance(other, ProgressStats):
            return NotImplemented
        return (
            self.cnt_total == other.cnt_total and
            self.cnt_complete == other.cnt_complete and
            self.cnt_in_progress == other.cnt_in_progress
        )

class GhJob(list[GhJobStep]):
    def __init__(self, job_id: int, name: str, status: GhStatus, conclusion: GhConclusion | None):
        self.job_id = job_id
        self.name = name
        self.status = status
        self.conclusion = conclusion
        super().__init__()

    def __eq__(self, other: object) -> bool:
        """
        Equality test for GhJob objects.  Compares the four scalar fields and the GhJobStep
        objects as a multiset.
        """
        if not isinstance(other, GhJob):
            return NotImplemented
        # Compare the four scalar fields
        if (
            self.job_id != other.job_id or
            self.name != other.name or
            self.status != other.status or
            self.conclusion != other.conclusion
        ):
            return False
        # Compare steps as a multiset (same elements, order doesn't matter)
        if len(self) != len(other):
            return False
        if self.get_progress() != other.get_progress():
            return False
        def step_as_tuple(step: GhJobStep):
            # Use .value if these are Enums, otherwise fall back to the raw object
            status_val = getattr(step.status, "value", step.status)
            concl_val = getattr(step.conclusion, "value", step.conclusion)
            return (step.name, status_val, concl_val)
        self_steps  = sorted(step_as_tuple(s) for s in self)
        other_steps = sorted(step_as_tuple(s) for s in other)
        return self_steps == other_steps

    def __hash__(self) -> int:
        """
        Hash function for GhJob object so they can be used as keys in dictionaries or sets.
        """
        def step_as_tuple(step: GhJobStep):
            status_val = getattr(step.status, "value", step.status)
            concl_val = getattr(step.conclusion, "value", step.conclusion)
            return (step.name, status_val, concl_val)
        steps_repr = tuple(sorted(step_as_tuple(s) for s in self))
        return hash((self.job_id, self.name, self.status, self.conclusion, steps_repr))

    # @classmethod
    # def construct_from_job_json_element(cls, fetcher: GhApiFetcher) -> Generator["GhJob", None, None]:
    #     """
    #     Given the jobs status json from a GhApiFetcher object, constructs GhJob and yields GhJob objects
    #     for insertion/replacement into a parent GhRun object.
    #
    #     Example jobs JSON:
    #         {
    #             "total_count": 7,
    #             "jobs": [
    #                 {
    #                 "id": 54831551871,
    #                 "run_id": 19179223310,
    #                 "workflow_name": "Release curvtools-v0.0.9",
    #                 "head_branch": "curvtools-v0.0.9",
    #                 "status": "completed",
    #                 "conclusion": "success",
    #                 ...
    #                 "steps": [
    #                     {
    #                     "name": "Set up job",
    #                     "status": "completed",
    #                     "conclusion": "success",
    #                     },
    #                     {
    #                     "name": "Set up job",
    #                     "status": "in-progress",
    #                     "conclusion": null,
    #                     },
    #                     ...
    #                 ]
    #                 }
    #                 ...
    #             ]
    #         }
    #     """
    #     import json
    #     jobs_json_data = json.loads(fetcher.get_gh_jobs_json())
    #     for job in jobs_json_data["jobs"]:
    #         # Construct a new GhJob object
    #         job_id = job['id']
    #         job_name = job['name']
    #         job_status = GhStatus(job.get("status", GhStatus.PENDING.value))
    #         job_conclusion = GhConclusion(job.get("conclusion", GhConclusion.NULL.value))
    #         ghjob = cls(job_id=job_id, name=job_name, status=job_status, conclusion=job_conclusion)
    #         for step_json_element in job["steps"]:
    #             ghjob.append(GhJobStep(name=step_json_element["name"], 
    #                                    status=GhStatus(step_json_element.get("status", GhStatus.PENDING.value)), 
    #                                    conclusion=GhConclusion(step_json_element.get("conclusion", GhConclusion.NULL.value))))
    #         yield ghjob

    def _get_steps_count_by_status(self) -> dict[GhStatus, int]:
        steps_by_status: dict[GhStatus, int] = {}
        for status in GhStatus:
            steps_by_status[status] = 0
        for step in self:
            steps_by_status[step.status] += 1
        assert steps_by_status[GhStatus.COMPLETED] + steps_by_status[GhStatus.IN_PROGRESS] + steps_by_status[GhStatus.PENDING] + steps_by_status[GhStatus.QUEUED] == len(self), \
            f"This assertion probably failed because more statuses were added to GhStatus enum: {steps_by_status[GhStatus.COMPLETED]} + {steps_by_status[GhStatus.IN_PROGRESS]} + {steps_by_status[GhStatus.PENDING] + steps_by_status[GhStatus.QUEUED]} != {len(self)}"
        return steps_by_status
    
    def get_progress(self) -> ProgressStats:
        steps_by_status = self._get_steps_count_by_status()
        return ProgressStats(cnt_complete=steps_by_status[GhStatus.COMPLETED], 
                             cnt_in_progress=steps_by_status[GhStatus.IN_PROGRESS], 
                             cnt_total=sum(steps_by_status.values()))
    
    def get_status_summary(self, indent: int = 0) -> str:
        print_str = ""
        steps_by_status = self._get_steps_count_by_status()
        for status, count in steps_by_status.items():
            print_str += f"\n{' ' * indent}{status.value.ljust(LONGEST_STATUS_NAME_LEN)}: {count}"
        
        progress = self.get_progress()
        print_str += f"\n{' ' * indent}Job percent complete: {progress.percent_complete:.2f}% ({progress.completed:.2f}/{progress.total:.2f})"
        return print_str

class GhRun(list[GhJob]):
    def __init__(self, gh_poller: GhPollingClient, run_id: int, name: str, status: GhStatus = GhStatus.PENDING, conclusion: GhConclusion = GhConclusion.NULL):
        self.gh_poller = gh_poller
        self.run_id = run_id
        self.name = name
        self.status = status
        self.conclusion = conclusion
        self.run_progress: ProgressStats = ProgressStats()
        super().__init__()
    
    @classmethod
    def construct_from_gh_poller(cls, gh_poller: GhPollingClient, poll_interval_sec: int = DEFAULT_INTERVALS['RUN_POLL']) -> "GhRun":
        import json
        run = None
        attempts = 0
        while run is None:
            attempts += 1
            if attempts > TIMEOUT_ATTEMPTS['RUN_POLL']:
                raise TimeoutError(f"Failed to get metadata for Run ID {gh_poller.run_id} after {TIMEOUT_ATTEMPTS['RUN_POLL'] * poll_interval_sec} seconds")
            try:
                ghcurr: GithubActionsCurrentState = gh_poller.poll_once()
            except RuntimeError as e:
                print(f"GitHub Actions run for run ID {gh_poller.run_id} not yet available...")
                continue
            finally:
                time.sleep(poll_interval_sec)
            run = cls(  gh_poller,
                        run_id=gh_poller.run_id,
                        name=ghcurr.run.get("name", ""), 
                        status=GhStatus(ghcurr.run.get("status", GhStatus.PENDING.value)), 
                        conclusion=GhConclusion(ghcurr.run.get("conclusion", GhConclusion.NULL.value)))
            break
        assert run is not None, "Object should have been constructed if we exited the loop without raising"
        return run

    def _get_jobs_count_by_status(self) -> dict[GhStatus, int]:
        jobs_by_status: dict[GhStatus, int] = {}
        for status in GhStatus:
            jobs_by_status[status] = 0
        for job in self:
            jobs_by_status[job.status] += 1
        return jobs_by_status

    def get_progress(self) -> ProgressStats:
        cnt_complete=sum(job.get_progress().cnt_complete for job in self)
        cnt_in_progress=sum(job.get_progress().cnt_in_progress for job in self)
        cnt_total=sum(job.get_progress().cnt_total for job in self)
        if self.status != GhStatus.COMPLETED:
            self.run_progress = ProgressStats(cnt_complete=cnt_complete, 
                                              cnt_in_progress=cnt_in_progress, 
                                              cnt_total=cnt_total)
        else:
            # once selt.status is marked completed, we force progress to 100%
            self.run_progress = ProgressStats(cnt_complete=cnt_total, 
                                              cnt_in_progress=0, 
                                              cnt_total=cnt_total)
        return self.run_progress

    def update(self) -> bool:
        """
        Updates the status and conclusion of the GhRun object from the GitHub Actions run JSON.
        Returns True if the state of the GhRun object changed, False if the new status and conclusion
        are identical to the current status and conclusion.

        Updates all the GhJob objects in the GhRun object from the GitHub Actions jobs JSON.
        Returns True if any part of state of this object changed, False if no fields were
        modified.
        """
        state_changed = False
        ghcurr: GithubActionsCurrentState = self.gh_poller.poll_once()
        new_status = GhStatus(ghcurr.run.get("status", GhStatus.PENDING.value))
        new_conclusion = GhConclusion(ghcurr.run.get("conclusion", GhConclusion.NULL.value))
        if new_status != self.status:
            self.status = new_status
            state_changed = True
        if new_conclusion != self.conclusion:
            self.conclusion = new_conclusion
            state_changed = True
        for job in ghcurr.jobs.get("jobs", []):
            job_id = int(job['id'])
            job_name = str(job['name'])
            job_status = GhStatus(job.get("status", GhStatus.PENDING.value))
            job_conclusion = GhConclusion(job.get("conclusion", GhConclusion.NULL.value))
            new_ghjob = GhJob(job_id=job_id, 
                              name=job_name, 
                              status=job_status, 
                              conclusion=job_conclusion)
            for jobstep in job["steps"]:
                new_ghjob.append(GhJobStep(name=jobstep["name"], 
                                           status=GhStatus(jobstep.get("status", GhStatus.PENDING.value)), 
                                           conclusion=GhConclusion(jobstep.get("conclusion", GhConclusion.NULL.value))))
            state_changed = self._upsert_job(new_ghjob) or state_changed
        return state_changed

    def _upsert_job(self, ghjob: GhJob) -> bool:
        """
        Upserts a GhJob object into the GhRun object.
        Returns True if the state of the GhRun object changed, False if the ghjob argument was
        identical to an existing GhJob object in the GhRun object.
        """
        state_changed = False
        existing_index = next((i for i, existing in enumerate(self) if getattr(existing, "job_id", None) == ghjob.job_id), None)
        if existing_index is not None:
            existing_ghjob_object = self[existing_index]
            if getattr(existing_ghjob_object, "status", None) == GhStatus.COMPLETED:
                # already completed, no need to update except for final conclusion
                existing_ghjob_object.conclusion = ghjob.conclusion
                state_changed = True if existing_ghjob_object.conclusion != ghjob.conclusion else state_changed
            else:
                # otherwise, replace the existing GhJob object with the new one
                self[existing_index] = ghjob
                state_changed = True if self[existing_index] != ghjob else state_changed
            # progress percentage is different so mark as changed
            state_changed = True if existing_ghjob_object.get_progress() != ghjob.get_progress() else state_changed
        else:
            # if no existing job object matched by id, append this job
            self.append(ghjob)
            state_changed = True
        return state_changed

    def get_child_job(self, job_id: int) -> GhJob:
        return next((job for job in self if job.job_id == job_id), None)

    def get_status_summary(self, indent: int = 0) -> str:
        jobs_by_status = self._get_jobs_count_by_status()
        print_str = f"GhRun(id={self.fetcher.run_id}, status={self.status.value}, jobs={sum(jobs_by_status.values())})"
        for key, cnt in jobs_by_status.items():
            print_str += f"\n{' ' * indent}{key.value.ljust(LONGEST_STATUS_NAME_LEN)}: {cnt}"

        print_str += "\n\nJobs:"
        longest_job_name_len = max(len(job.name) for job in self)
        for job in self:
            print_str += f"\n{' ' * indent}{(job.name + ':').ljust(longest_job_name_len)} {job.get_status_summary(indent=indent + 2)}"

        progress = self.get_progress()
        print_str += f"\n\nRun percent complete: {progress.percent_complete:.2f}% ({progress.completed:.2f}/{progress.total:.2f})"
        return print_str
