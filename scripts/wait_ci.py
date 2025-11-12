#!/usr/bin/env python3

import argparse
import os
import subprocess
from enum import Enum, IntEnum
import sys
import time
from wait_ci_lib.gh_run import GhRun, GhJob, GhStatus, GhConclusion, get_gh_jobs_json, get_gh_run_json, DEFAULT_INTERVALS
from curvpyutils.multi_progress import DisplayOptions, MessageLineOpt, SizeOpt, StackupOpt, BoundingRectOpt, BarColors, WorkerProgressGroup
from curvpyutils.multi_progress.display_options import Style
from rich.console import Console
from rich.text import Text

console = Console()

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

class PrintSeverity(IntEnum):
    NORMAL = 0
    WARNING = (1 << 0)
    ERROR = (1 << 1)

class PrintVerbosityLevel(IntEnum):
    NORMAL = 0
    VERBOSE = 1
    DEBUG = 2

def main() -> None:
    args = parse_args()
    prog_name = os.path.basename(sys.argv[0])
    run_id = int(args.GH_ACTION_RUN_ID)

    def print_out(message: str|Text, severity: PrintSeverity = PrintSeverity.NORMAL, verbosity: PrintVerbosityLevel = PrintVerbosityLevel.NORMAL) -> None:
        if args.verbosity >= verbosity.value or severity.value >= PrintSeverity.WARNING.value:
            print_args = []
            prog_name_text = Text(f"[{prog_name}] ", style=Style(color="dark_blue", bold=False))
            print_args.append(prog_name_text)
            if severity.value >= PrintSeverity.ERROR.value:
                prefix_text = Text(f"{severity.name}: ", style=Style(color="red", bold=False))
                print_args.append(prefix_text)
            elif severity.value >= PrintSeverity.WARNING.value:
                prefix_text = Text(f"{severity.name}: ", style=Style(color="yellow", bold=False))
                print_args.append(prefix_text)
            if isinstance(message, str):
                message_text = Text(message, style=Style(color="white", bold=False))
            else:
                message_text = message
            print_args.append(message_text)
            console.print(*print_args)

    print_out(f"watching github action run {run_id}...", verbosity=PrintVerbosityLevel.NORMAL)

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
    latest = {}
    run.update_run_status(get_gh_run_json(run_id))
    for new_ghjob in GhJob.construct_from_job_json_element(get_gh_jobs_json(run_id)):
        run.upsert_job(new_ghjob)
        worker_group.add_worker(worker_id=new_ghjob.job_id)
        latest[new_ghjob.job_id] = new_ghjob.get_progress().percent_complete
    worker_group.update_all(latest=latest)
    with worker_group.with_live(console=console) as live:
        while not worker_group.is_finished() and run.status != GhStatus.COMPLETED:
            sleep_for_sec:float = float(DEFAULT_INTERVALS['JOBS_POLL'])
            run.update_run_status(get_gh_run_json(run_id))
            for new_ghjob in GhJob.construct_from_job_json_element(get_gh_jobs_json(run_id)):
                run.upsert_job(new_ghjob)
                worker_group.add_worker(worker_id=new_ghjob.job_id)
                latest[new_ghjob.job_id] = new_ghjob.get_progress().percent_complete
                worker_group.update_all(latest=latest)
            if run.status == GhStatus.COMPLETED:
                # final update
                if run.conclusion == GhConclusion.SUCCESS:
                    worker_group.complete_all()
                else:
                    worker_group.update_display_options(new_display_options=DisplayOptions(
                        Message=MessageLineOpt(message="CI run completed with failure", message_style=Style(color="red", bold=True)),
                        OverallBarColors=BarColors.red(),
                        WorkerBarColors=BarColors.red(),
                        BoundingRect=BoundingRectOpt(title=f"FAILED: Run {run.run_id}", 
                                                     border_style=Style(color="red", bold=True)),
                    ))
                    worker_group.update_all(latest=latest)
                break
            else:
                if sleep_for_sec > 0.0:
                    time.sleep(0.1)
                    sleep_for_sec -= 0.1
                worker_group.update_all(latest=latest)


    print_out("----------------------------------------", verbosity=PrintVerbosityLevel.DEBUG)

    cmd = ["gh", "run", "watch", "--interval", "10", "--exit-status", str(run_id)]

    try:
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            check=True,
            timeout=10*60    # 10 minutes timeout
        )
    except subprocess.TimeoutExpired as e:
        print_out("CI run timed out", severity=PrintSeverity.ERROR)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print_out(f"stdout: {e.stdout}", verbosity=PrintVerbosityLevel.DEBUG)
        print_out(f"stderr: {e.stderr}", verbosity=PrintVerbosityLevel.DEBUG)
        if e.returncode == 143:
            print_out("CI run was cancelled by user", severity=PrintSeverity.WARNING)
            sys.exit(0)
        elif e.returncode == 1:
            import re
            find_status_match = re.search(r"completed with '(.*)'", e.stdout)
            ci_run_failed_text = Text('CI run failed', Style(color="red", bold=True))
            if find_status_match:
                out_text = Text.assemble(
                    ci_run_failed_text, 
                    ' (',
                    Text(f'{find_status_match.group(1)}', Style(color="dark_red", bold=True)),
                    ')'
                )
            else:
                out_text = Text.assemble(
                    ci_run_failed_text, 
                )
            print_out(out_text, severity=PrintSeverity.ERROR)
            sys.exit(1)
        else:
            raise e
    sys.exit(0)

if __name__ == "__main__":
    main()


