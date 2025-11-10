#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import time
from wait_ci_lib.gh_run import GhRun, GhJob, GhStatus, get_gh_jobs_json, get_gh_run_json, DEFAULT_INTERVALS
from curvpyutils.multi_progress import DisplayOptions, MessageLineOpt, SizeOpt, StackupOpt, BoundingRectOpt, BarColors, WorkerProgressGroup
from curvpyutils.multi_progress.display_options import Style


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description=(
            "Use `gh` to repeatedly check the CI status for a GitHub Actions run. "
            "Exits with the same status as `gh run watch`."
        ),
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress all output (only exit status is returned).",
    )
    group.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v or -vv)",
    )

    parser.add_argument(
        "GH_ACTION_RUN_ID",
        help="GitHub Actions run ID to watch.",
    )

    args = parser.parse_args()

    # Map verbosity according to spec:
    # default -> 0, -q -> -1, -v -> 1, -vv -> 2 (cap at 2)
    if args.quiet:
        verbosity = -1
    else:
        verbosity = min(args.verbose, 2)
    args.verbosity = verbosity

    return args


def main() -> None:
    args = parse_args()
    prog_name = os.path.basename(sys.argv[0])
    run_id = int(args.GH_ACTION_RUN_ID)

    def print_out(message: str) -> None:
        if args.verbosity >= 0:
            print(f"[{prog_name}] {message}")

    def print_verbose(message: str) -> None:
        if args.verbosity >= 1:
            print(f"[{prog_name}] {message}")

    print_out(f"watching github action run {run_id}...")

    def get_worker_name(x: int) -> str:
        return run.get_child_job(x).name
    
    run: GhRun = GhRun.construct_from_run_json_query(run_id)
    for new_ghjob in GhJob.construct_from_job_json_element(get_gh_jobs_json(run_id)):
        run.upsert_job(new_ghjob)

    display_options = DisplayOptions(
        Message=MessageLineOpt(message="Waiting for CI...", message_style=Style(color="red", bold=True)),
        Transient=False,
        FnWorkerIdToName=get_worker_name,
        OverallNameStr=f"{run.name}",
        OverallNameStrStyle=Style(color="dark_blue", bold=True),
        OverallBarColors=BarColors.default(),
        WorkerBarColors=BarColors.default(),
        Size=SizeOpt.MEDIUM,
        Stackup=StackupOpt.OVERALL_WORKERS,
        BoundingRect=BoundingRectOpt(title=f"GitHub Actions Run {run.run_id}", 
                                     border_style=Style(color="blue", bold=True)),
    )
    worker_group = WorkerProgressGroup(display_options=display_options)
    latest = {i: 0.0 for i in range(len(run))}
    run.update_run_status(get_gh_run_json(run_id))
    for new_ghjob in GhJob.construct_from_job_json_element(get_gh_jobs_json(run_id)):
        run.upsert_job(new_ghjob)
        worker_group.add_worker(worker_id=new_ghjob.job_id)
        latest[new_ghjob.job_id] = new_ghjob.get_progress().percent_complete
    while True:
        sleep_for_sec:float = float(DEFAULT_INTERVALS['JOBS_POLL'])
        run.update_run_status(get_gh_run_json(run_id))
        for new_ghjob in GhJob.construct_from_job_json_element(get_gh_jobs_json(run_id)):
            run.upsert_job(new_ghjob)
            if new_ghjob.job_id not in latest: latest[new_ghjob.job_id] = 0.0
            latest[new_ghjob.job_id] = max(latest[new_ghjob.job_id], min(100.0, max(0.0, new_ghjob.get_progress().percent_complete)))        
        with worker_group.with_live() as live:
            while not worker_group.is_finished():
                if run.status != GhStatus.COMPLETED:
                    worker_group.update_all(latest)
                    time.sleep(0.1)
                    sleep_for_sec -= 0.1
                    if (sleep_for_sec <= 0.0):
                        break
                    continue
                else:
                    # final update
                    if run.status == GhStatus.COMPLETED:
                        latest = {i: 100.0 for i in range(len(run))}
                    worker_group.complete_all()
                    time.sleep(2)
                    break
        if run.status == GhStatus.COMPLETED:
            break

    print_verbose("----------------------------------------")

    cmd = ["gh", "run", "watch", "--interval", "10", "--exit-status", str(run_id)]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    print_verbose(result.stdout)
    print_verbose(result.stderr)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()


