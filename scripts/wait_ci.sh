#!/usr/bin/env bash

#
# ./wait_ci.sh [-v|-q] [GH_ACTION_RUN_ID]
#
# Use `gh` to repeatedlycheck the CI status for run GH_ACTION_RUN_ID.
# Exit when it finishes:
#  - Exit 0 if it succeeded
#  - Exit non-zero if it failed
#

GH_ACTION_RUN_ID=""

# set these to '/dev/null' to suppress output; set to '/dev/stdout' to show output
GH_RUN_WATCH_OUTPUT_DESTINATION=/dev/null
OUTPUT_DESTINATION=/dev/stdout

# parse args
while [ $# -gt 0 ]; do
    case "$1" in
        -v|--verbose)
            GH_RUN_WATCH_OUTPUT_DESTINATION=/dev/stdout
            OUTPUT_DESTINATION=/dev/stdout
            shift
            ;;
        -q|--quiet)
            OUTPUT_DESTINATION=/dev/null
            GH_RUN_WATCH_OUTPUT_DESTINATION=/dev/null
            shift
            ;;
        -h|--help)
            echo "usage: $0 [-v/-verbose | -q/-quiet] <GH_ACTION_RUN_ID>" >&2
            exit 2
            ;;
        --)
            shift
            break
            ;;
        -*)
            echo "error: unknown option: $1" >&2
            echo "usage: $0 [-v] <GH_ACTION_RUN_ID>" >&2
            exit 2
            ;;
        *)
            if [ -z "$GH_ACTION_RUN_ID" ]; then
                GH_ACTION_RUN_ID="$1"
            else
                echo "error: unexpected argument: $1" >&2
                echo "usage: $0 [-v] <GH_ACTION_RUN_ID>" >&2
                exit 2
            fi
            shift
            ;;
    esac
done

if [ -z "$GH_ACTION_RUN_ID" ]; then
    echo "error: missing required positional argument: GH_ACTION_RUN_ID" >&2
    echo "usage: $0 [-v] <GH_ACTION_RUN_ID>" >&2
    exit 1
fi

printf "[%s] %s\n" "$(basename $0)" "watching github action run $GH_ACTION_RUN_ID..." > $OUTPUT_DESTINATION 2>&1;
printf "[%s] %s\n" "$(basename $0)" "----------------------------------------" > $GH_RUN_WATCH_OUTPUT_DESTINATION 2>&1;
gh run watch --interval 10 --exit-status $GH_ACTION_RUN_ID > $GH_RUN_WATCH_OUTPUT_DESTINATION 2>&1
printf "[%s] %s\n" "$(basename $0)" "----------------------------------------" > $GH_RUN_WATCH_OUTPUT_DESTINATION 2>&1;
EXIT_STATUS=$?
if [ $EXIT_STATUS -eq 0 ]; then
    printf "[%s] %s\n" "$(basename $0)" "CI passed: exit 0" > $OUTPUT_DESTINATION 2>&1;
else
    printf "[%s] %s\n" "$(basename $0)" "CI failed: exit $EXIT_STATUS" > $OUTPUT_DESTINATION 2>&1;
fi
exit $EXIT_STATUS