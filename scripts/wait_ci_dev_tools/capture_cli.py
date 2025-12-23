#!/usr/bin/env -S uv run --script --all-packages

"""
Helper CLI for developers to capture and inspect GitHub Actions JSON responses.

This mirrors the previous CLI that lived inside `wait_ci_lib/gh/gh_api.py` so that the
production library only provides `GhApiFetcher` while dev tooling sits beside it.
"""

from datetime import datetime, timezone
import argparse
import json
import os
import sys
import time
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.traceback import install, Traceback
from wait_ci_lib.gh.gh_api import GhApiFetcher
from wait_ci_lib.gh.gh_api_parallel import GhPollingClient
from wait_ci_lib.gh.github_actions_current_state import GithubActionsCurrentState
from .summarize_capture_file import CaptureFileSummarizer

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch GitHub Actions run and jobs JSON from the GitHub API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    $ capture_cli.py --capture-mode=capture-json 19305894952 --capture-path=/tmp/captures
    $ capture_cli.py --capture-mode=use-captured-json --capture-path=/tmp/captures/gh_run_19305894952_capture.json
    $ capture_cli.py -S --capture-mode=use-captured-json --capture-path=/tmp/captures/gh_run_19305894952_capture.json
    $ capture_cli.py -T --capture-mode=use-captured-json --capture-path=/tmp/captures/gh_run_19305894952_capture.json

Capture file is always called "gh_run_{run_id}_capture.json".
    - for 'capture-json' mode: the '{run_id}' part is replaced by the actual run id
    - for 'use-captured-json' mode: the '{run_id}' part is a number that is treated as the actual run id
""",
    )
    parser.add_argument(
        "run_id",
        metavar="RUN_ID",
        type=int,
        nargs="?",
        default=None,
        help="the run ID to fetch for CAPTURE_JSON mode; ignored for USE_CAPTURED_JSON mode",
    )
    parser.add_argument(
        "--capture-mode",
        type=str,
        default="capture-json",
        choices=[
            GhApiFetcher.CaptureMode.CAPTURE_JSON.value.lower().replace("_", "-"),
            GhApiFetcher.CaptureMode.USE_CAPTURED_JSON.value.lower().replace("_", "-"),
        ],
        help="capture mode to use (default: %(default)s)",
    )
    parser.add_argument(
        "--capture-path",
        type=str,
        default=None,
        help="path of JSON capture file (must be a path to a JSON file for 'use-captured-json' mode; for 'capture-json' mode, we treat this as the directory to write 'gh_run_{run_id}_capture.json' to)",
    )
    summarization_group = parser.add_argument_group("Summarization")
    summarization_group_mutually_exclusive = summarization_group.add_mutually_exclusive_group()
    summarization_group_mutually_exclusive.add_argument(
        "-S",
        dest="summarize",
        action="store_const",
        const="text",
        help="summarize the capture file as text",
    )
    summarization_group_mutually_exclusive.add_argument(
        "-T",
        dest="summarize",
        action="store_const",
        const="tree",
        help="summarize the capture file after loading it as a tree",
    )
    parser.set_defaults(summarize=None)
    args = parser.parse_args()
    if "capture-json".startswith(args.capture_mode):
        args.capture_mode = GhApiFetcher.CaptureMode.CAPTURE_JSON
    elif "use-captured-json".startswith(args.capture_mode):
        args.capture_mode = GhApiFetcher.CaptureMode.USE_CAPTURED_JSON
    else:
        parser.error(f"Invalid capture mode: {args.capture_mode}")

    if (args.capture_path == GhApiFetcher.CaptureMode.USE_CAPTURED_JSON) and (
        args.capture_path is None or not os.path.exists(args.capture_path)
    ):
        parser.error(
            "For USE_CAPTURED_JSON mode, you must supply a capture path of a capture file that exists"
        )
    elif args.summarize and args.capture_mode == GhApiFetcher.CaptureMode.CAPTURE_JSON:
        parser.error("Summarization is not possible for CAPTURE_JSON mode")
    return args


def main():
    install()

    def print_json(title: str, json_str: str) -> None:
        json_renderable = JSON(json_str, indent=4)
        panel = Panel(
            json_renderable,
            title=title,
            style="green",
            border_style="white",
            highlight=True,
        )
        console.print(panel)

    capture_interval_sec = 1
    args = parse_args()

    if args.capture_mode == GhApiFetcher.CaptureMode.CAPTURE_JSON:
        run_id = int(args.run_id)
        fetcher: GhApiFetcher | None = None
        client: GhPollingClient | None = None
        try:
            fetcher = GhApiFetcher(
                run_id=run_id,
                capture_mode=GhApiFetcher.CaptureMode.CAPTURE_JSON,
                capture_dir=args.capture_path if args.capture_path else os.getcwd(),
            )
            client = GhPollingClient(fetcher, append_to_capture=True)
            while True:
                result: GithubActionsCurrentState = client.poll_once()
                console.print(f"epoch_offset: {result.epoch_offset:.3f}s", style="blue")
                console.print(f"run:")
                console.print(f"{json.dumps(result.run, indent=4)}", style="green")
                console.print(f"jobs:")
                console.print(f"{json.dumps(result.jobs, indent=4)}", style="green")
                if result.run["status"] == "completed":
                    console.print(
                        f"Run completed with status: {result.run['status']}, conclusion: {result.run['conclusion']}",
                        style="bold white",
                    )
                    break
                time.sleep(capture_interval_sec)
            if fetcher is not None:
                console.print("Saving capture...", style="green bold")
                fetcher.save_capture()
        except KeyboardInterrupt:
            console.print("Keyboard interrupt received...", style="white bold")
            sys.exit(0)
        except Exception as e:
            console.print(f"Error: {e}", style="bold red")
            console.print(
                Traceback.from_exception(type(e), e, e.__traceback__),
                style="bold yellow",
            )
            sys.exit(1)
        finally:
            if client is not None:
                client.close()
    elif args.capture_mode == GhApiFetcher.CaptureMode.USE_CAPTURED_JSON:
        fetcher = GhApiFetcher(
            run_id=None,
            capture_mode=GhApiFetcher.CaptureMode.USE_CAPTURED_JSON,
            capture_filename=args.capture_path,
        )
        try:
            if args.summarize:
                summarizer = CaptureFileSummarizer(args.capture_path)
                summarizer.summarize(as_rich_tree=(args.summarize == "tree"))
            else:
                capture_json_str = ""
                with open(args.capture_path, "r", encoding="utf-8") as f:
                    capture_json_str = f.read()
                print_json(f"capture at {datetime.now(timezone.utc).timestamp():.3f}s", capture_json_str)
        except KeyboardInterrupt:
            console.print("Keyboard interrupt received, exiting...", style="white bold")
            sys.exit(0)
        except Exception as e:
            console.print_exception(show_locals=True)
            sys.exit(1)


if __name__ == "__main__":
    main()

