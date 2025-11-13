#!/usr/bin/env -S uv run --script --all-packages

"""
This module provides a class for representing the current state of a GitHub Actions run and jobs.
"""

import json
from typing import Any
from dataclasses import dataclass, field
from typing import Any, Tuple

################################################################################
#
# Classes
#
################################################################################

@dataclass
class GithubActionsCurrentState:
    # data has this structure:
    #   {
    #     "run": {...object in the JSON returned by the run fetch...},
    #     "jobs": {...object in the JSON returned by the jobs fetch...},
    #     "epoch_offset": float,  # essentially the time stamp when this data became valid
    #   }
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_combined_result(
        cls, result: Tuple[str, str, float]
    ) -> "GithubActionsCurrentState":
        run_json_str, jobs_json_str, epoch_offset = result
        run_data = json.loads(run_json_str)
        jobs_data = json.loads(jobs_json_str)
        return cls(
            data={"run": run_data, "jobs": jobs_data, "epoch_offset": epoch_offset}
        )

    @property
    def run(self) -> Any:
        return self.data["run"]

    @property
    def jobs(self) -> Any:
        return self.data["jobs"]

    @property
    def epoch_offset(self) -> float:
        return self.data["epoch_offset"]
