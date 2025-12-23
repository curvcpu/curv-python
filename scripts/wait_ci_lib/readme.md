# Testing this Script

Here is how test data is created.

## Making a JSON Capture File

  - cd into the repo root
  - Start a capture that waits for the next CI run to file:
  
    ```sh
    $ scripts/wait_ci_lib/gh/gh_api.py $(scripts/get-current-ci.sh 2>/dev/null) --capture-mode=capture-json --capture-path=scripts/wait_ci_lib/test/test_vectors/captures/
    ```
  - In another terminal, push something to the repo that will trigger a CI run (e.g., `git commit -m "test" && git push`)

  - You should see the captured JSON start being printed to your console.  
  
  - When the CI run is complete, the program will exit and write the capture file to the capture path directory.

  - You can now view a tree summary of the capture JSON like this:

    ```sh
    $ scripts/wait_ci_lib/gh/gh_api.py -T --capture-mode=use-captured-json  --capture-path=scripts/wait_ci_lib/test/test_vectors/captures/gh_run_19332482748_capture.json
    ```

  - You can now test the GhRun and GhJob classes by running:

    ```sh
    $ scripts/wait_ci_lib/gh/gh_run.py scripts/wait_ci_lib/test/test_vectors/captures/gh_run_19322111192_capture.json
    ```

  - You should see the status of the GhRun object being printed to your console along with the timestamps of each JSON response.  The times are floats representing seconds since the start of the capture.

## Using Capture Files for Testing and Debugging

  - `wait_ci.py` will "re-play" a capture supplied via `--debug-capture-file/-D` flag without making any Github API calls.  This is useful for testing and debugging:

    ```sh
    $ ./scripts/wait_ci.py -D scripts/wait_ci_lib/test/test_vectors/captures/gh_run_19332482748_capture.json
    ```

      - Note that no run ID is needed; it's derived from the capture file's filename.
