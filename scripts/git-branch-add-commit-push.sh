#!/usr/bin/env bash

# Help if no args or any arg is "-h" or "--help"
show_help=false
for arg in "$@"; do
	if [[ "$arg" == "-h" || "$arg" == "--help" ]] ; then show_help=true; break; fi
done
if [[ $# -eq 0 ]]; then show_help=true; fi

printf "arg1: %s\n" "$1"
printf "arg2: %s\n" "$2"
printf "arg3: %s\n" "$3"
printf "arg4: %s\n" "$4"
printf "arg5: %s\n" "$5"
printf "arg6: %s\n" "$6"
printf "arg7: %s\n" "$7"
printf "arg8: %s\n" "$8"
printf "arg9: %s\n" "$9"
printf "arg10: %s\n" "$10"
printf "arg11: %s\n" "$11"
printf "arg12: %s\n" "$12"
printf "arg13: %s\n" "$13"
printf "arg14: %s\n" "$14"
printf "arg15: %s\n" "$15"
printf "arg16: %s\n" "$16"

# if invoked as `git branch-off` or similar, construct the program name as that
# and then mutate $@ in place to remove first two args
if [[ "$0" == "git" ]]; then
	prog="$0 $1"
	shift
else
	prog=$(basename "${BASH_SOURCE[0]}")
fi

if [[ "$show_help" == "true" ]]; then
	cat <<EOF
Takes all unstaged/unstaged changes and commits them onto a NEW branch and
optionally pushes them to the remote.

usage:
  ${prog} [feat|fix] <new-branch> [commit message]

examples:
  ${prog} fix bug-in-script "my commit message"
  ${prog} feat new-feature "add new feature"
  ${prog} feat new-feature

notes:
  Starts from current HEAD (whatever branch you're on).
  Does this: 
   • git feat <new-branch> -r
   • <prompt for message if not provided>
   • git magic -a -m 'message'
   • <prompt for push? [y/N]> → git push
EOF
	exit 1
fi

# make sure we have git-extras installed
if ! git extras --version >/dev/null 2>&1; then
	echo "requires 'git-extras' to be installed, e.g., brew install git-extras"
	exit 1
fi

# make sure no extra args
if [[ $# -gt 3 ]]; then
	echo "error: only three arguments allowed: [feat|fix] <new-branch> [message]" >&2
	exit 1
fi

# make sure first arg is 'feat' or 'fix'
if [[ "$1" != "feat" && "$1" != "fix" ]]; then
	echo "error: first arg must be 'feat' or 'fix'"
	exit 1
fi

# basic branch name validation per git's rules
if ! git check-ref-format --branch "$2" > /dev/null 2>&1; then
	echo "error: '$2' is not a valid branch name" >&2
	exit 1
fi

# branch must not already exist
if git show-ref --verify --quiet "refs/heads/$2"; then
	echo "error: branch '$2' already exists" >&2
	exit 1
fi

################################################################################
# 
# main function
#
################################################################################

git-branch-add-commit-push() {
  	local feat_or_fix new_branch msg

	feat_or_fix=$1
	new_branch=$2

	# Get message (arg or prompt)
	if [[ $# -eq 3 ]]; then
		msg=$3
	else
		msg=""
		while true; do
			trap 'echo; echo "Commit cancelled"; return 1' INT
			read -r -p "Commit message: " msg
			trap - INT
			if [[ -z "${msg//[[:space:]]/}" ]]; then
				echo "error: commit message cannot be empty; try again" >&2
			else
				break
			fi
		done
	fi

	# creates & checks out new branch
	git feature -a "$feat_or_fix" "$new_branch" -r || { echo "error: failed to create new branch '$new_branch'" >&2; return 1; }

	# stage all unstaged + commit
	git magic -a -m "$msg" || { echo "error: failed to commit" >&2; return 1; }

	# Optional push
	local ans ans_lower
	read -r -p "Push now? [y/N] " ans
	ans="${ans:-n}"  # default to "n" if empty (ENTER pressed)
	ans_lower="${ans,,}"  # convert to lowercase for case-insensitive matching
	case "${ans_lower:0:1}" in  # check first character only
		y) 
			if git rev-parse --git-dir >/dev/null 2>&1 && git remote get-url origin >/dev/null 2>&1; then
				git push || { echo "error: failed to push" >&2; return 1; }
			else
				echo "note: no 'origin' remote configured; skipping push" >&2
			fi
		;;
		*) echo "skipping push" >&2;;
	esac

	return 0
}

################################################################################
# 
# main execution
#
################################################################################

git-branch-add-commit-push "$@"
exit $?
