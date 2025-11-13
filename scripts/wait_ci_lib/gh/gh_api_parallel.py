#!/usr/bin/env -S uv run --script --all-packages

"""
This module provides classes for threading two workers to fetch GitHub Actions run and 
jobs JSON from the GitHub API in parallel, and then merging them into a GithubActionsCurrentState 
object.

The GithubActionsCurrentState object has this structure:
  {
    "run": {...object in the JSON returned by the run fetch...},
    "jobs": {...object in the JSON returned by the jobs fetch...},
    "epoch_offset": float,  # essentially the time stamp when this data became valid
  }
"""

from enum import Enum, auto
from datetime import datetime, timezone
import subprocess
import time
import sys
import os
import argparse
import json
import re
from typing import Any, Callable, Tuple, Union
import threading
import queue
import pytest
from dataclasses import dataclass, field
from rich.console import Console
from rich.traceback import install, Traceback
from .gh_types import ResultType, CombinedResultType
from .github_actions_current_state import GithubActionsCurrentState
from .gh_api import GhApiFetcher

console = Console()

################################################################################
#
# Classes
#
################################################################################

class GhDualWorker:
    """
    Owns two worker threads:
      - worker 1 calls fetch_run()
      - worker 2 calls fetch_jobs()

    Each worker has:
      - a request queue (depth 1)
      - a result queue (depth 1)

    The main thread is expected to:
      - call trigger_once() to enqueue one request on each worker
      - then call get_results() to block until both responses are ready
    """

    def __init__(
        self,
        fetch_run_fn: Callable[[], ResultType],
        fetch_jobs_fn: Callable[[], ResultType],
    ) -> None:
        self._fetch_run_fn = fetch_run_fn
        self._fetch_jobs_fn = fetch_jobs_fn

        # queues depth 1 as requested
        self._run_request_queue: queue.Queue[object] = queue.Queue(maxsize=1)
        self._run_result_queue: queue.Queue[ResultType] = queue.Queue(maxsize=1)
        self._jobs_request_queue: queue.Queue[object] = queue.Queue(maxsize=1)
        self._jobs_result_queue: queue.Queue[ResultType] = queue.Queue(maxsize=1)

        self._stop_event = threading.Event()

        self._run_thread = threading.Thread(
            target=self._worker_loop,
            args=(self._run_request_queue, self._run_result_queue, self._fetch_run_fn),
            daemon=True,
        )
        self._jobs_thread = threading.Thread(
            target=self._worker_loop,
            args=(
                self._jobs_request_queue,
                self._jobs_result_queue,
                self._fetch_jobs_fn,
            ),
            daemon=True,
        )

        self._run_thread.start()
        self._jobs_thread.start()

    @staticmethod
    def _worker_loop(
        request_queue: "queue.Queue[object]",
        result_queue: "queue.Queue[ResultType]",
        fn: Callable[[], ResultType],
    ) -> None:
        """
        Generic worker:
          - blocks on request_queue.get()
          - if sentinel (None), exits
          - otherwise calls fn(), puts result into result_queue
        """
        while True:
            req = request_queue.get()  # blocking
            if req is None:  # sentinel for shutdown
                break
            try:
                result: ResultType = fn()
            except Exception as e:
                result: Exception = e
            result_queue.put(result)

    # ---------- public API for your main / containing class ----------

    def trigger_once(self) -> None:
        """
        Enqueue one request on each worker.

        Assumes the caller only calls this again after get_results()
        has drained the previous result, so maxsize=1 never blocks.
        """
        self._run_request_queue.put(object())
        self._jobs_request_queue.put(object())

    def get_results(self, timeout: float | None = None) -> CombinedResultType:
        """
        Block until both workers have finished their current task and
        put their results in their respective result queues.

        You can pass a timeout if you want, in seconds.
        """
        try:
            run_res = self._run_result_queue.get(timeout=timeout)
            jobs_res = self._jobs_result_queue.get(timeout=timeout)
        except queue.Empty:
            return TimeoutError(f"Timeout waiting for results after {timeout} seconds")

        # Otherwise, run_res and jobs_res should both be tuples[str, float]
        if (isinstance(run_res, Exception)):
            return run_res
        if (isinstance(jobs_res, Exception)):
            return jobs_res
        assert (len(run_res) == 2), f"run_res is not a tuple of length 2: {len(run_res)}"
        assert (len(jobs_res) == 2), f"jobs_res is not a tuple of length 2: {len(jobs_res)}"
        return (run_res[0], jobs_res[0], max(run_res[1], jobs_res[1]))

    def close(self) -> None:
        """Signal both workers to exit and join the threads."""
        # send sentinel
        self._run_request_queue.put(None)
        self._jobs_request_queue.put(None)

        self._run_thread.join()
        self._jobs_thread.join()




class GhPollingClient:
    """
    Polls the GitHub API for run and jobs JSON in parallel.
    """

    def __init__(self, fetcher: GhApiFetcher, append_to_capture: bool = False):
        """
        Initialize the polling client.

        Args:
            - fetcher: the GhApiFetcher to use for fetching the run and jobs JSON
              (inversion of control pattern with GhApiFetcher's member functions)
            - fn_append_to_capture: if provided, call this function with the fetched data
              as an object once it is available.  If None, then fn_append_to_capture is
              never called.

        """
        self.run_id = fetcher.run_id
        self._workers = GhDualWorker(
            fetch_run_fn=fetcher.get_gh_run_json,
            fetch_jobs_fn=fetcher.get_gh_jobs_json,
        )
        if append_to_capture:
            self._fn_append_to_capture = fetcher.append_to_capture
        else:
            self._fn_append_to_capture = None

    def poll_once(self) -> GithubActionsCurrentState:
        """
        Kick off both API calls in parallel and wait for both results.

        Returns:
            GithubActionsCurrentState object containing the 'run' and 'jobs' JSON keys,
            each pointing to a decoded JSON object, and the 'epoch_offset'
            timestamp key when the data became valid.

        Raises:
            Exception: Since we are back on the main thread here, we raise
            any returned exception.
        """
        self._workers.trigger_once()
        result: CombinedResultType = self._workers.get_results()
        if isinstance(result, Exception):
            raise result
        if not (
            isinstance(result, tuple)
            and len(result) == 3
            and isinstance(result[0], str)
            and isinstance(result[1], str)
            and isinstance(result[2], float)
        ):
            raise ValueError(f"Unexpected result type: {type(result)}")
        # convert to our return type, which parses the JSON strings into objects
        ret = GithubActionsCurrentState.from_combined_result(result)
        # if we have a function to call, call it with the data
        if self._fn_append_to_capture is not None:
            self._fn_append_to_capture(ret.data)
        return ret

    def close(self) -> None:
        """Signal both workers to exit and join the threads."""
        self._workers.close()
