#!/usr/bin/env -S uv run --script --all-packages

"""
This module provides a class for fetching GitHub Actions run and jobs JSON from the GitHub API.
"""

from enum import Enum
from datetime import datetime, timezone
import subprocess
import os
import json
import re
from typing import Any, Union

################################################################################
#
# Classes
#
################################################################################

class GhApiFetcher:
    """
    Fetches GitHub Actions run and jobs JSON from the GitHub API.

    There are three modes of operation:
        - NORMAL: In normal mode, we just query the GitHub API directly for json and return it.
        - CAPTURE_JSON: Same as normal mode, except we capture the JSON responses from the GitHub API to a
          dict which can be saved to a json file at the end of the run and "re-played" later.
        - USE_CAPTURED_JSON: If json responses were previously captured, we can use them instead of
          actually querying the GitHub API.  This is for testing/debugging.
    """

    class CaptureMode(Enum):
        NORMAL = "normal"
        CAPTURE_JSON = "capture_json"
        USE_CAPTURED_JSON = "use_captured_json"

    def __init__(
        self,
        run_id: str | int | None,
        capture_mode: CaptureMode = CaptureMode.NORMAL,
        capture_filename: str = "gh_run_{run_id}_capture.json",
        capture_dir: str = os.getcwd(),
    ):
        """
        Normal mode:
          - Supply run_id, omit all other arguments
          - JSON responses are fetched from the GitHub API directly
        Capture mode:
          - Supply run_id, capture_mode=CaptureMode.CAPTURE_JSON, and an optional capture_filename
            (default is "gh_run_{run_id}_capture.json"; if you deviate, be sure your filename
            contains '{run_id}' somewhere in its name so it can be read back later)
              - One way to use the default filename but control where it gets written is to
                provide a capture_dir argument, which will be prepended to capture_filename to
                form the full path of the capture file.
          - JSON responses are fetched from the GitHub API and captured to a file
          - When the run is complete, call save_capture() to save the captured JSON responses to the
            file specified by capture_filename.
        Use captured previously captured JSON:
          - Do not supply any run_id (set it to None), do provide capture_mode=CaptureMode.USE_CAPTURED_JSON,
            and a capture_filename that is a real capture file that was previously saved by a previous run.
            The file must contain the run ID in its name, e.g., "gh_run_19305894952_capture.json". If
            capture_dir is provided, it will be prepended to capture_filename to form the full path
            of the capture file.
          - JSON responses are read from a file instead of fetched from the GitHub API.
            The response you will get at any given point in time is the most recent response that
            has been captured at or slightly before that time.
        Args:
          - run_id: the run ID to poll
          - capture_mode: the capture mode to use
          - capture_filename: the filename to use for the capture file
          - capture_dir: (optional) a directory that can be prepended to capture_filename to form the full path
            to the capture file.  If not provided, the current working directory is used.
        """
        self.capture_mode = capture_mode
        if self.capture_mode == self.CaptureMode.USE_CAPTURED_JSON:
            assert (
                run_id is None
            ), "For USE_CAPTURED_JSON, do not supply a run_id; it will be determined from the capture file's name"
            self.capture_filename = capture_filename
            self.run_id = self._get_run_id_from_capture_filename(self.capture_filename)
            self.capture_filename = os.path.join(capture_dir, self.capture_filename)
            self.captured_jsons = self._load_capture()
        elif self.capture_mode == self.CaptureMode.CAPTURE_JSON:
            assert run_id is not None, "For CAPTURE_JSON, you must supply a run_id"
            self.run_id = str(run_id)
            self.capture_filename = capture_filename.format(run_id=self.run_id)
            self.capture_filename = os.path.join(capture_dir, self.capture_filename)
            self.captured_jsons: list[dict[str, Any]] = []
        elif self.capture_mode == self.CaptureMode.NORMAL:
            assert run_id is not None, "For NORMAL, you must supply a run_id"
            self.run_id = str(run_id)
            self.capture_filename = None
            self.captured_jsons = None
        else:
            raise ValueError(f"Invalid capture mode: {self.capture_mode}")

        # initialize the start time for the capture timestamps, used both for reading and writing captures
        self.start_time = datetime.now(timezone.utc).timestamp()

    def _get_run_id_from_capture_filename(self, capture_filename: str) -> str:
        """
        The capture filename must contain a 10 or more digit number somewhere, which
        must be the run ID.  If it does not, raise a ValueError.

        Args:
          capture_filename: the filename to extract the run ID from

        Returns:
          the run ID as a string

        Raises:
          ValueError: if the capture filename does not contain a run ID in its name
        """
        match = re.search(r"(\d{10,})", capture_filename)
        if not match:
            raise ValueError(
                f"Capture filename '{capture_filename}' does not contain a run ID in its name"
            )
        return match.group(1)

    def get_gh_run_json(self) -> Union[tuple[str, float], Exception]:
        """
        Fetch the GitHub Actions run JSON from the GitHub API. This function is meant to be
        called by a worker thread in an inversion of control pattern with GhPollingClient.

        Args:
            None

        Returns:
            tuple[str, float] if successful, Exception if not

        Raises:
            None. If an exception occurs, it is caught and returned instead of the normal
            return value.
        """
        try:
            # Use captured JSON: return the most recent response that was captured in the capture file
            if self.capture_mode == self.CaptureMode.USE_CAPTURED_JSON:
                # Find the greatest index whose epoch_offset <= now_epoch_offset; if none, use the earliest index
                eligible_idx_list: list[int] = []
                for i,item in enumerate(self.captured_jsons):
                    if "epoch_offset" in item and item["epoch_offset"] <= self.now_epoch_offset:
                        eligible_idx_list.append(i)
                chosen_idx = max(eligible_idx_list) if eligible_idx_list else 0
                json_str = json.dumps(self.captured_jsons[chosen_idx]["run"], indent=4)
                return json_str, self.now_epoch_offset
            else:
                # Normal operation: fetch the run JSON from the GitHub API
                cmd = [
                    "gh",
                    "api",
                    "repos/{owner}/{repo}/actions/runs/" + self.run_id,
                    "--paginate",
                ]
                result = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        f"Failed to get GitHub Actions run for run ID {self.run_id}: {result.stderr}"
                    )
                stdout = str(result.stdout)
                # if self.capture_mode == self.CaptureMode.CAPTURE_JSON:
                #     self._capture_run_json(stdout)
                return stdout, self.now_epoch_offset
        except Exception as e:
            return e

    def get_gh_jobs_json(self) -> Union[tuple[str, float], Exception]:
        """
        Fetch the GitHub Actions jobs JSON from the GitHub API. This function is meant to be
        called by a worker thread in an inversion of control pattern with GhPollingClient.

        Args:
            None

        Returns:
            tuple[str, float] if successful, Exception if not

        Raises:
            None. If an exception occurs, it is caught and returned instead of the normal
            return value.
        """
        try:
            # Use captured JSON: return the most recent response that was captured in the capture file
            if self.capture_mode == self.CaptureMode.USE_CAPTURED_JSON:
                # Find the greatest index whose epoch_offset <= now_epoch_offset; if none, use the earliest index
                eligible_idx_list: list[int] = []
                for i,item in enumerate(self.captured_jsons):
                    # console.log(f"item[{i}]: epoch_offset={item['epoch_offset']} <= self.now_epoch_offset={self.now_epoch_offset}")
                    if "epoch_offset" in item and item["epoch_offset"] <= self.now_epoch_offset:
                        eligible_idx_list.append(i)
                # console.log(f"eligible_idx_list: {eligible_idx_list}")
                chosen_idx = max(eligible_idx_list) if eligible_idx_list else 0
                json_str = json.dumps(self.captured_jsons[chosen_idx]["jobs"], indent=4)
                # console.log(f"chosen_idx: {chosen_idx}, json_str: {json_str}")
                return json_str, self.now_epoch_offset
            else:
                # Normal operation: fetch the jobs JSON from the GitHub API
                cmd = [
                    "gh",
                    "api",
                    "repos/{owner}/{repo}/actions/runs/" + self.run_id + "/jobs",
                    "--paginate",
                ]
                result = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        f"Failed to get GitHub Actions jobs by run ID {self.run_id}: {result.stderr}"
                    )
                stdout = str(result.stdout)
                # if self.capture_mode == self.CaptureMode.CAPTURE_JSON:
                #     self._capture_jobs_json(stdout)
                return stdout, self.now_epoch_offset
        except Exception as e:
            return e

    @property
    def now_epoch_offset(self) -> float:
        """
        The number of seconds since the start time of the capture.
        """
        return datetime.now(timezone.utc).timestamp() - self.start_time

    # def _capture_run_json(self, json_str: str) -> None:
    #     self.captured_jsons["run"][self.now_epoch_offset] = json_str

    # def _capture_jobs_json(self, json_str: str) -> None:
    #     self.captured_jsons["jobs"][self.now_epoch_offset] = json_str

    def append_to_capture(self, data: dict[str, Any]) -> None:
        """
        Append the given data to the capture. data is expected to have the structure:
        {
            "run": {...object in the JSON returned by the run fetch...},
            "jobs": {...object in the JSON returned by the jobs fetch...},
            "epoch_offset": float,  # essentially the time stamp when this data became valid
        }
        """
        assert isinstance(data, dict), f"data is not a dictionary: {type(data)}"
        assert "run" in data, "data must contain a 'run' key"
        assert "jobs" in data, "data must contain a 'jobs' key"
        assert "epoch_offset" in data, "data must contain an 'epoch_offset' key"
        self.captured_jsons.append(data)

    def save_capture(self) -> None:
        # Save the captured JSON responses to the file specified by capture_filename
        os.makedirs(os.path.dirname(self.capture_filename), exist_ok=True)
        with open(self.capture_filename, "w") as f:
            json.dump(self.captured_jsons, f, indent=4)

    def _load_capture(self) -> dict[str, dict[float, str]]:
        # Load the captured JSON responses from the file specified by capture_filename
        if not self.capture_filename:
            raise ValueError("Capture filename not set")
        if not os.path.exists(self.capture_filename):
            raise FileNotFoundError(f"Capture file '{self.capture_filename}' not found")
        with open(self.capture_filename, "r") as f:
            loaded: list[dict[str, Any]] = json.load(f)
            # Make sure incoming json fits our expected schema: an array of
            # {"run": ..., "jobs": ..., "epoch_offset": ...} objects
            normalized: list[dict[str, Any]] = []
            for item in loaded:
                assert isinstance(item, dict), f"item is not a dictionary: {type(item)}"
                assert "run" in item, "item must contain a 'run' key"
                assert "jobs" in item, "item must contain a 'jobs' key"
                assert "epoch_offset" in item, "item must contain an 'epoch_offset' key"
                assert isinstance(
                    item["run"], dict
                ), f"item['run'] is not a dictionary: {type(item['run'])}"
                assert isinstance(
                    item["jobs"], dict
                ), f"item['jobs'] is not a dictionary: {type(item['jobs'])}"
                assert isinstance(
                    item["epoch_offset"], float
                ), f"item['epoch_offset'] is not a string: {type(item['epoch_offset'])}"
                normalized.append(
                    {
                        "run": item["run"],
                        "jobs": item["jobs"],
                        "epoch_offset": float(item["epoch_offset"]),
                    }
                )
            normalized.sort(key=lambda x: x["epoch_offset"])
            return normalized
