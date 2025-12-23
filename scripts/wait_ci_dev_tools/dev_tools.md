# Developer Capture Tooling

This directory houses the CLI that records and inspects GitHub Actions captures so that the core
`wait_ci_lib` package stays focused on production data fetching.

## Creating a Capture

- From within this directory, run:

  ```sh
  $ ./capture_cli.py --capture-mode=capture-json \
      $(./get-current-ci.sh 2>/dev/null) \
      --capture-path=./test_vectors/captures/
  ```

- Push a commit in another terminal to trigger CI. The CLI will stream API responses and, once the run
  completes, write `gh_run_<run_id>_capture.json` into the capture path directory.

## Summarizing a Capture

- To pretty-print a recorded capture:

  ```sh
  $ ./capture_cli.py \
      -T \
      --capture-mode=use-captured-json \
      --capture-path=./test_vectors/captures/gh_run_19332482748_capture.json
  ```

## Replaying a Capture

- `wait_ci.py -D` replays a capture without hitting the GitHub API. That command uses the same
  `GhApiFetcher` implementation that production code relies on, so the capture proves the loader
  logic while letting you watch progress bars locally:

  ```sh
  $ ../wait_ci.py -D ./test_vectors/captures/gh_run_19332482748_capture.json
  ```
