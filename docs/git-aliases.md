# CI and PR Automation Scripts

Here are some git aliases I use with this repo and a demonstration of how they work.

## `git` Aliases

Add these aliases to `.git/config`:

```shell
[alias]
    # `git gci` - wait for current CI to complete; exit 0 on success, non-zero on failure
    gci = "!REPO_ROOT=$(git rev-parse --show-toplevel); \
        ${REPO_ROOT}/scripts/wait_ci.py"

    # `git branch-off` - moves all unstaged changes to a new branch, commits and 
    # pushes
    branch-off = "!REPO_ROOT=$(git rev-parse --show-toplevel); \
        json=$(~/scripts/ai-git-messages.py -b -c -v -e); \
        featfix=$(printf '%s' \"$json\" | jq -r '.feat_or_fix'); \
        branch_name=$(printf '%s' \"$json\" | jq -r '.branch_name'); \
        msg=$(printf '%s' \"$json\" | jq -r '.commit_message'); \
        ${REPO_ROOT}/scripts/git-branch-add-commit-push.sh \
            \"$featfix\" \"$branch_name\" \"$msg\""

    # `git pr-[open,mergeable,merge]` - sequence of 2 commands to open PR then 
    # merge from the cli
    pr-open = "!json=$(~/scripts/ai-git-messages.py -p -c -v); \
        title=$(printf '%s' \"$json\" | jq -r '.title'); \
        body=$(printf '%s' \"$json\" | jq -r '.body'); \
        gh pr create --web --title \"$title\" --body \"$body\""
    pr-merge = "!json=$(gh pr view --json number,title,mergeable); \
        number=$(printf '%s' \"$json\" | jq -r '.number'); \
        title=$(printf '%s' \"$json\" | jq -r '.title'); \
        printf '%s' \"$json\" | jq -e '.mergeable == \"MERGEABLE\"' 1>&2 || { \
            echo \"not mergeable\"; \
            exit 1; \
        }; \
        gh pr merge --squash -d \
            --subject \"Merge PR #${number}: ${title}\" \
            --body \"\" \
        && git gci"
```

## Usage

Suppose you have made some changes on `main` and now wish to turn them into a PR:

```sh
# create a new branch `feat/new-feature` with the changes + 
# commit + push
$ ./scripts/git-branch-add-commit-push.sh feat/new-feature "add new feature"
```

or, let AI generate the branch name and commit message (you'll be able to edit it first):

```sh
$ git branch-off
```

Then open the PR, with pre-editing of the commit message in the browser:

```sh
# Let AI generate the commit message and edit in the browser 
# before opening the PR
$ git pr-open
```

When ready to merge, `git pr-merge` will try to merge, display progress, and exit 0 on success, non-zero on failure:

```sh
# try to merge and wait for merge CI to pass
$ git pr-merge || echo "failed to merge"
```
