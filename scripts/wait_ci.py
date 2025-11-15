#!/usr/bin/env python3

import argparse
import os
import subprocess
from enum import Enum, IntEnum
import sys
import time
from wait_ci_lib.gh import GhRun, GhStatus, GhConclusion, DEFAULT_INTERVALS, GhPollingClient, GhApiFetcher
from curvpyutils.multi_progress import DisplayOptions, MessageLineOpt, SizeOpt, SizeOptCustom, StackupOpt, BoundingRectOpt, BarColors, WorkerProgressGroup
from rich.console import Console
from rich.text import Text
from rich.style import Style
from rich.traceback import install, Traceback
from typing import Optional, Callable

console = Console()

################################################################################
# console logger
################################################################################

class PrintSeverity(IntEnum):
    NORMAL = 0
    WARNING = (1 << 0)
    ERROR = (1 << 1)

class PrintVerbosityLevel(IntEnum):
    NORMAL = 0
    VERBOSE = 1
    DEBUG = 2

def mk_print_out_fn(args: Optional[argparse.Namespace] = None) -> Callable[[str|Text, PrintSeverity, PrintVerbosityLevel], None]:
    if args is None:
        args = argparse.Namespace()
        args.verbosity = 0
    def print_out(message: str|Text, severity: PrintSeverity = PrintSeverity.NORMAL, verbosity: PrintVerbosityLevel = PrintVerbosityLevel.NORMAL) -> None:
        prog_name = os.path.basename(sys.argv[0])
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
    return print_out

print_out = mk_print_out_fn()

################################################################################
# helper functions
################################################################################

def get_latest_commit_gh_run_id(RETRY_TIMEOUT_SEC: int = 30, DELAY_BETWEEN_ATTEMPTS_SEC: int = 1) -> int:
    """
    Get the latest commit's Github Actions CI run id. We retry once per second until RETRY_TIMEOUT_SEC is reached.

    Args:
        RETRY_TIMEOUT_SEC: The number of seconds to retry before timing out
        DELAY_BETWEEN_ATTEMPTS_SEC: The number of seconds to wait between attempts
    
    Together, these determine how many attempts will be made before timing out.

    Returns:
        The run id for the latest commit's Github Actions CI run
    
    Raises:
        subprocess.CalledProcessError: if any subprocess command exists non-zero
        RuntimeError: If the run id for the latest commit's Github Actions CI run cannot be found after MAX_ATTEMPTS attempts
    """

    MAX_ATTEMPTS: int = RETRY_TIMEOUT_SEC // DELAY_BETWEEN_ATTEMPTS_SEC

    attempts = 0
    run_id = None
    while attempts < MAX_ATTEMPTS:
        # get the latest commit sha pushed to Github
        cmd = ["git", "rev-parse", "HEAD"]
        latest_commit_sha_result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            check=True)
        if latest_commit_sha_result.returncode != 0:
            raise subprocess.CalledProcessError(latest_commit_sha_result.returncode, cmd)
        latest_commit_sha = latest_commit_sha_result.stdout.strip()

        # get the run id for latest_commit_sha
        cmd = [ "gh", 
                "run", 
                "list", 
                "--json", "createdAt,headSha,name,status,conclusion,databaseId", 
                "-L10", 
                "--jq", 
                f"map(select(.headSha==\"{latest_commit_sha}\")) | max_by(.createdAt)? | .databaseId? // empty"
            ]
        run_id_result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            check=True)
        if run_id_result.returncode != 0:
            raise subprocess.CalledProcessError(run_id_result.returncode, cmd)
        run_id = run_id_result.stdout.strip()
        if run_id:
            return int(run_id)
        
        print_out(f"Could not get run id for latest commit yet (attempt {attempts + 1} of {MAX_ATTEMPTS})", severity=PrintSeverity.WARNING)
        time.sleep(float(DELAY_BETWEEN_ATTEMPTS_SEC))
        attempts += 1
    raise TimeoutError(f"Could not get run id for latest commit after {RETRY_TIMEOUT_SEC} seconds of retries")

################################################################################
# cli argument parsing
################################################################################

def make_parent_parser() -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    """Create and configure the parent parser for common arguments.

    Purpose of parent parser is to initially detect whether -D/--debug-capture-file
    was provided.  If that's the case, the main parser does not want GH_ACTION_RUN_ID,
    which is otherwise normally an optional positional argument.

    Returns:
        A tuple of (parent_parser, parsed_args) where parent_parser is the
        configured ArgumentParser and parsed_args contains the parsed arguments
        from parse_known_args().
    """
    parent_parser = argparse.ArgumentParser(add_help=False)

    group = parent_parser.add_argument_group("Verbosity")
    group_mutex = group.add_mutually_exclusive_group()
    group_mutex.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress all output (only exit status is returned).",
    )
    group_mutex.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v or -vv)",
    )

    debug_group = parent_parser.add_argument_group("Debugging")
    debug_group.add_argument(
        "-D",
        "--debug-capture-file",
        metavar="DEBUG_CAPTURE_FILE",
        type=str,
        default=None,
        help="Path to a capture file to use for debugging; in this case GH_ACTION_RUN_ID is ignored",
    )

    # Parse known args first to check for debug-capture-file
    args, remaining = parent_parser.parse_known_args()
    return parent_parser, args

def parse_args() -> argparse.Namespace:
    # Get parent parser and its parsed args
    parent_parser, parent_args = make_parent_parser()

    # Main parser
    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description=(
            "Use `gh` to repeatedly check the CI status for a GitHub Actions run. "
            "Exits with the same status as `gh run watch`."
        ),
        parents=[parent_parser],
    )

    # Only add GH_ACTION_RUN_ID if debug-capture-file is not provided
    if parent_args.debug_capture_file is None:
        parser.add_argument(
            "GH_ACTION_RUN_ID",
            nargs="?",
            default=None,
            help="GitHub Actions run ID to watch (default: latest commit's Github Actions CI run)",
            type=int,
        )

    args = parser.parse_args()

    # Map verbosity according to spec:
    # default -> 0, -q -> -1, -v -> 1, -vv -> 2 (cap at 2)
    if args.quiet:
        verbosity = -1
    else:
        verbosity = min(args.verbose, 2)
    args.verbosity = verbosity

    # set the global print_out function to the one that was just created
    global print_out
    print_out = mk_print_out_fn(args)

    # if they don't provide a GH_ACTION_RUN_ID, try to get it from the latest commit
    if args.GH_ACTION_RUN_ID is None:
        try:
            args.GH_ACTION_RUN_ID = get_latest_commit_gh_run_id()
        except Exception as e:
            print_out(f"Unable to get latest commit's Github Actions CI run ID:", severity=PrintSeverity.ERROR)
            print_out(f"  {e}", severity=PrintSeverity.ERROR)
            print_out(f"Hint: either provide a GH_ACTION_RUN_ID as a positional argument and/or make sure you actually pushed your last commit to Github", severity=PrintSeverity.ERROR)
            sys.exit(1)
    return args

################################################################################
# main function
################################################################################

def main() -> None:
    install(show_locals=True)
    args = parse_args()

    def get_live_console(verbosity: int) -> Console:
        if verbosity >= PrintVerbosityLevel.NORMAL.value:
            return console
        else:
            # this will never be displayed to stdout
            return Console(quiet=True)

    fetcher: GhApiFetcher | None = None
    client: GhPollingClient | None = None
    run: GhRun | None = None
    try:
        if args.debug_capture_file is None:
            fetcher = GhApiFetcher(run_id=args.GH_ACTION_RUN_ID)
        else:
            fetcher = GhApiFetcher(
                run_id=None, 
                capture_mode=GhApiFetcher.CaptureMode.USE_CAPTURED_JSON, 
                capture_filename=args.debug_capture_file)
        run_id = fetcher.run_id
        print_out(f"watching github action run {run_id}...", verbosity=PrintVerbosityLevel.NORMAL)
        client = GhPollingClient(fetcher)

        run = GhRun.construct_from_gh_poller(client)

        display_options = DisplayOptions(
            Message=MessageLineOpt(message=f"https://github.com/curvcpu/curv-python/actions/runs/{run.run_id}", message_style=Style(color="dodger_blue1", bold=False, link=f"https://github.com/curvcpu/curv-python/actions/runs/{run.run_id}")),
            Transient=False,
            FnWorkerIdToName=lambda worker_id: f"{run.get_child_job(worker_id).name}",
            OverallNameStr=f"{run.name}",
            OverallNameStrStyle=Style(color="gray66", bold=True),
            OverallBarColors=BarColors.default(),
            WorkerBarColors=BarColors.default(),
            Size=SizeOptCustom(
                job_bar_args=SizeOptCustom.BarArgs(width=80, fn_elapsed=None, fn_remaining=None), 
                overall_bar_args=SizeOptCustom.BarArgs(width=60, fn_elapsed=None),
                max_names_length=-40,
            ),
            Stackup=StackupOpt.OVERALL_WORKERS_MESSAGE,
            BoundingRect=BoundingRectOpt(title=f"GitHub Actions Run {run.run_id}", 
                                         border_style=Style(color="cornflower_blue", bold=True)),
        )
        worker_group = WorkerProgressGroup(display_options=display_options)
        latest = {}
        changed: bool = run.update()
        if changed:
            for ghjob in run:
                worker_group.add_worker(worker_id=ghjob.job_id)
                latest[ghjob.job_id] = ghjob.get_progress().percent_complete
            worker_group.update_all(latest=latest)
        with worker_group.with_live(console=get_live_console(args.verbosity)) as live:
            first_iteration = True
            while first_iteration or run.status != GhStatus.COMPLETED:
                first_iteration = False
                sleep_for_sec:float = float(DEFAULT_INTERVALS['JOBS_POLL'])
                changed: bool = run.update()
                if changed:
                    for ghjob in run:
                        worker_group.add_worker(worker_id=ghjob.job_id)
                        latest[ghjob.job_id] = ghjob.get_progress().percent_complete
                    worker_group.update_all(latest=latest)
                if run.status == GhStatus.COMPLETED:
                    # final update
                    if run.conclusion == GhConclusion.SUCCESS:
                        worker_group.update_display_options(new_display_options=DisplayOptions(
                            Message=MessageLineOpt(message="✅ CI completed successfully", message_style=Style(color="dodger_blue1", bold=True)),
                            BoundingRect=BoundingRectOpt(title=f"SUCCESS: Run {run.run_id}", 
                                                         border_style=Style(color="spring_green1", bold=True)),
                        ))
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
                    time.sleep(sleep_for_sec)
                    break
                else:
                    time.sleep(sleep_for_sec)
                    worker_group.update_all(latest=latest)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print_out(f"Error: {e}", severity=PrintSeverity.ERROR)
        console.print(Traceback.from_exception(type(e), e, e.__traceback__))
        sys.exit(1)
    finally:
        if client is not None:
            client.close()

    if run is not None:
        if run.conclusion == GhConclusion.SUCCESS:
            print_out("✓ CI run completed successfully", severity=PrintSeverity.NORMAL)
            sys.exit(0)
        else:
            print_out("✗ CI run completed with failure", severity=PrintSeverity.ERROR)
            sys.exit(1)
    else:
        print_out("fatal: no Github Actions CI run found", severity=PrintSeverity.ERROR)
        sys.exit(1)

    # print_out("----------------------------------------", verbosity=PrintVerbosityLevel.DEBUG)

    # cmd = ["gh", "run", "watch", "--interval", "10", "--exit-status", str(run_id)]

    # try:
    #     result = subprocess.run(
    #         cmd, 
    #         stdout=subprocess.PIPE, 
    #         stderr=subprocess.PIPE, 
    #         text=True, 
    #         check=True,
    #         timeout=10*60    # 10 minutes timeout
    #     )
    # except subprocess.TimeoutExpired as e:
    #     print_out("CI run timed out", severity=PrintSeverity.ERROR)
    #     sys.exit(1)
    # except subprocess.CalledProcessError as e:
    #     print_out(f"stdout: {e.stdout}", verbosity=PrintVerbosityLevel.DEBUG)
    #     print_out(f"stderr: {e.stderr}", verbosity=PrintVerbosityLevel.DEBUG)
    #     if e.returncode == 143:
    #         print_out("CI run was cancelled by user", severity=PrintSeverity.WARNING)
    #         sys.exit(0)
    #     elif e.returncode == 1:
    #         import re
    #         find_status_match = re.search(r"completed with '(.*)'", e.stdout)
    #         ci_run_failed_text = Text('CI run failed', Style(color="red", bold=True))
    #         if find_status_match:
    #             out_text = Text.assemble(
    #                 ci_run_failed_text, 
    #                 ' (',
    #                 Text(f'{find_status_match.group(1)}', Style(color="dark_red", bold=True)),
    #                 ')'
    #             )
    #         else:
    #             out_text = Text.assemble(
    #                 ci_run_failed_text, 
    #             )
    #         print_out(out_text, severity=PrintSeverity.ERROR)
    #         sys.exit(1)
    #     else:
    #         raise e
    # sys.exit(0)

if __name__ == "__main__":
    main()


