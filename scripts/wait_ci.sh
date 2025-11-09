#
# make wait-ci
#
# Use `gh` to check the CI status for the last commit.
# Exit 0 if it succeeded, non-zero if it failed.
#

# set to '/dev/null' to suppress output; set to '/dev/stdout' to show output
OUTPUT_DESTINATION=/dev/stdout

# get the last commit sha
LAST_COMMIT_SHA=$(git rev-parse HEAD)

# get the github action id for the last commit
while true; do
    GH_ACTION_ID=$(gh run list --json createdAt,headSha,name,status,conclusion,databaseId -L10 --jq '.[] | select(.headSha=="'"$LAST_COMMIT_SHA"'") | .databaseId');
	if [ -n "$GH_ACTION_ID" ]; then
	  echo "found github action id: $GH_ACTION_ID for commit ${LAST_COMMIT_SHA:0:8}" > $OUTPUT_DESTINATION 2>&1;
	  break;
	else
	  echo "notice: could not get github action id for commit ${LAST_COMMIT_SHA:0:8} yet..." > $OUTPUT_DESTINATION 2>&1;
	  sleep 5;
	fi
done

printf "%s\n" "----------------------------------------" > $OUTPUT_DESTINATION 2>&1;
gh run watch --interval 10 --exit-status $GH_ACTION_ID > $OUTPUT_DESTINATION 2>&1
printf "%s\n" "----------------------------------------" > $OUTPUT_DESTINATION 2>&1;
EXIT_STATUS=$?
if [ $EXIT_STATUS -eq 0 ]; then
    echo "CI passed" > $OUTPUT_DESTINATION 2>&1;
else
    echo "CI failed" > $OUTPUT_DESTINATION 2>&1;
fi
exit $EXIT_STATUS