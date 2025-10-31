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
    parser.add_argument("tag", metavar="TAG", nargs=1, help='a recently published tag, e.g., `curvpyutils-v0.0.7`')
    args = parser.parse_args()
    return args

def main() -> int:
    args = parse_args()
    try:
        timeout = int(os.environ.get("TIMEOUT", "360"))
    except ValueError:
        timeout = 360
    token = os.environ.get("GITHUB_TOKEN")

    start = time.time()
    while True:
        try:
            print(f"fetching status for {get_status_url_for_tag(args.tag[0])}", flush=True)
            data = fetch_status(args.tag[0], token)
            statuses = data.get("statuses", [])
            if statuses:
                state = str(statuses[0].get("state", "")).lower()
                if state == "success":
                    # optional: print final target_url
                    print("[SUCCESS] " + statuses[0].get("target_url", ""), flush=True)
                    return 0
                if state in {"failure", "error"}:
                    print("[FAILURE] " + statuses[0].get("target_url", ""), flush=True)
                    return 2
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
