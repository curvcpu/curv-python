#!/usr/bin/env python3
"""
wait_gh_tag_status.py TAG

Polls:
  https://api.github.com/repos/curvcpu/curv-python/commits/TAG/status
once per second until:
  - statuses[0].state == "success" -> exit 0
  - statuses[0].state in {"failure", "error"} or TIMEOUT -> exit 2

Env:
  TIMEOUT       (int seconds, default 360)
  GITHUB_TOKEN  (optional, for higher rate limits)
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import argparse

OWNER = "curvcpu"
REPO = "curv-python"
API = "https://api.github.com"

def get_status_url_for_tag(tag: str) -> str:
    return f"{API}/repos/{OWNER}/{REPO}/commits/{tag}/status"

def fetch_status(tag: str, token: str | None) -> dict:
    url = get_status_url_for_tag(tag)
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "curv-python-status-checker",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} for {url}")
        return json.load(resp)

def parse_args():
    parser = argparse.ArgumentParser(description='wait for github tag action to report success')
    parser.add_argument("-d", "--debug", action="store_true", help='enable debug output')
    parser.add_argument("tag", metavar="TAG", nargs=1, help='a recently published tag, e.g., `curvpyutils-v0.0.7`')
    args = parser.parse_args()
    return args

def main() -> int:
    args = parse_args()
    debug = args.debug
    try:
        timeout = int(os.environ.get("TIMEOUT", "360"))
    except ValueError:
        timeout = 360
    token = os.environ.get("GITHUB_TOKEN")

    start = time.time()
    while True:
        try:
            if debug:
                print(f"DEBUG: fetching status for {get_status_url_for_tag(args.tag[0])}", flush=True)
            data = fetch_status(args.tag[0], token)
            if debug:
                print(f"DEBUG: Full response JSON:\n{json.dumps(data, indent=2)}", flush=True)

            # Check combined state first (top-level "state" field)
            combined_state = data.get("state", "").lower()
            if debug:
                print(f"DEBUG: Combined state: '{combined_state}'", flush=True)

            statuses = data.get("statuses", [])
            if debug:
                print(f"DEBUG: statuses array length: {len(statuses)}", flush=True)

            # Look for publish status in the statuses array
            publish_status = None
            for status in statuses:
                context = status.get("context", "")
                if debug:
                    print(f"DEBUG: Checking status with context: '{context}'", flush=True)
                if "publish" in context.lower():
                    publish_status = status
                    if debug:
                        print(f"DEBUG: Found publish status: {json.dumps(status, indent=2)}", flush=True)
                    break

            # Use combined state if available, otherwise check publish status
            if combined_state == "success" and publish_status:
                state_to_check = str(publish_status.get("state", combined_state)).lower()
            elif combined_state:
                state_to_check = combined_state
            elif publish_status:
                state_to_check = str(publish_status.get("state", "")).lower()
            else:
                state_to_check = None

            if debug:
                print(f"DEBUG: Final state to check: '{state_to_check}'", flush=True)

            if state_to_check == "success":
                if publish_status:
                    print("[SUCCESS] " + publish_status.get("target_url", ""), flush=True)
                else:
                    print("[SUCCESS] Workflow completed successfully", flush=True)
                return 0
            elif state_to_check in {"failure", "error"}:
                if publish_status:
                    print("[FAILURE] " + publish_status.get("target_url", ""), flush=True)
                else:
                    print("[FAILURE] Workflow failed", flush=True)
                return 2
            else:
                if debug:
                    print("DEBUG: Status not yet available or still pending, waiting...", flush=True)
            # else: still pending (empty array)
        except urllib.error.HTTPError as e:
            # 404 while GH wires things up; keep waiting
            if e.code in (404, 403):
                pass
            else:
                # treat other HTTP errors as failure
                return 2
        except Exception:
            # network/parse error -> treat as transient, keep waiting
            pass

        if time.time() - start >= timeout:
            return 2
        time.sleep(5)

if __name__ == "__main__":
    sys.exit(main())
