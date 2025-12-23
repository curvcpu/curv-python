#!/usr/bin/env bash

#
# ./get-current-ci.sh - print the Github Actions CI run id for the current commit
#
# Prints just the id to stdout, followed by a newline and exits with status 0.
# (Other logging goes to stderr.)
#

while true; do
	LAST_COMMIT_SHA=$(git rev-parse HEAD)
    GH_ACTION_ID=$(gh run list --json createdAt,headSha,name,status,conclusion,databaseId -L10 --jq 'map(select(.headSha=="'"$LAST_COMMIT_SHA"'")) | max_by(.createdAt)? | .databaseId? // empty')
	if [ -n "$GH_ACTION_ID" ]; then
	  echo "[$(basename $0)] found github action run id: '${GH_ACTION_ID}' for commit '${LAST_COMMIT_SHA:0:8}'" >&2
	  echo "$GH_ACTION_ID"
	  exit 0
	else
	  echo "[$(basename $0)] notice: could not get github action id for commit '${LAST_COMMIT_SHA:0:8}' yet..." >&2
	  sleep 5
	fi
done

echo "[$(basename $0)] error: could not get github action id for commit '${LAST_COMMIT_SHA:0:8}'" >&2
exit 1