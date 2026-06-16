#!/bin/bash
# push_marking.sh — Commit and push marking results into each submission's git repository.
#
#   This is useful to create a branch `marking` from the `submission` branch/tag, add marking results (e.g., under a `marking/` folder), and push it back to the remote repository.
# 
# 
# For each subdirectory in <submissions-folder> (one per student/team repo):
#   - If the remote already has a "marking" branch: check it out and pull.
#   - Otherwise: check out the "submission" branch/tag and create a new "marking" branch from it.
#     If neither exists on the remote, the repo is skipped.
#   - Stage everything under the "marking/" folder, commit, and push to origin.
#
# USAGE:
#   push_marking.sh <submissions-folder> [--dry-run]
#
#   <submissions-folder>  Directory whose immediate subdirs are local clones of submission repos.
#   --dry-run             Print all git commands without executing them.
#
# CONFIGURATION (edit variables below):
#   BRANCH          Name of the branch to create/update (default: "marking").
#   COMMIT_MESSAGE  Commit message used when pushing results (default: "Add marking result").
#
# @author Sebastian Sardina (ssardina@gmail.com) - 2026
set -euo pipefail   # https://www.shkodenko.com/what-string-set-eeuo-pipefail-in-shell-script-does-mean/


# CONFIGURATION: adapt as required :-)
ME=$(basename "$0")
DRY_RUN=false
TIME_SLEEP=3
COMMIT_MESSAGE="Add to marking runs result: rooms combinable"
BRANCH="marking"
SUBMISSIONS_DIR="$1"
ONE_RUN=false
REPO_NAME=""

usage() {
    echo "USAGE: $ME <submissions-folder> [--dry-run|--one]"
    exit 1
}

# if wrong number of arguments, print usage and exit
[[ $# -lt 1 ]] && usage


# we cannot handle the "next"
# for arg in "$@"; do
#     [[ "$arg" == "--dry-run" ]] && DRY_RUN=true
#     [[ "$arg" == "--one" ]] && ONE_RUN=true
# done

# process arguments
shift # Move past the first argument (submissions folder)
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift # Move past the flag
            ;;
        --one)
            ONE_RUN=true
            shift # Move past the flag
            ;;
        --repo)
            if [[ -n "$2" && "$2" != -* ]]; then
                REPO_NAME="$2"
                shift 2 # Move past both the flag and its value
            else
                echo "Error: Argument --repo requires a non-empty value." >&2
                exit 1
            fi
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

run() {
    if $DRY_RUN; then
        echo "[DRY-RUN] $*"
    else
        "$@"
    fi
}

remote_branch_exists() {
    local dir="$1" branch="$2"
    git -C "$dir" ls-remote --heads origin "$branch" | grep -q "refs/heads/$branch"
}

# returns true if a branch OR tag with the given name exists on the remote
remote_ref_exists() {
    local dir="$1" ref="$2"
    git -C "$dir" ls-remote --heads --tags origin "$ref" | grep -q .
}

echo "Submissions folder : $SUBMISSIONS_DIR"
echo "Dry run            : $DRY_RUN"
echo "One run            : $ONE_RUN"
echo

COUNTER=0
for dir in "$SUBMISSIONS_DIR"/*/; do
    [[ -d "$dir" ]] || continue

    # Extract the folder name (strips everything up to the last slash)
    # e.g., "submission/a9/" or "submission/a9" -> "a9"
    current_folder="${dir%/}"     # Strip trailing slash if it exists
    current_folder="${current_folder##*/}" # Strip everything before the last slash

    # If REPO_NAME is set, skip any directory that doesn't match it
    if [[ -n "$REPO_NAME" && "$current_folder" != "$REPO_NAME" ]]; then
        continue
    fi


    (( COUNTER++ )) || true
    URL=$(git -C "$dir" remote get-url origin \
        | sed 's|git@\(.*\):\(.*\)\.git|https://\1/\2|; s|git@\(.*\):\(.*\)|https://\1/\2|')
    echo "=====> [$COUNTER] $dir  ($URL)"

    ################################################################
    # 1. Create or reuse the marking branch
    ################################################################
    if remote_branch_exists "$dir" "$BRANCH"; then
        echo "Branch '$BRANCH' exists on remote — checking out and pulling"
        run git -C "$dir" checkout "$BRANCH"
        run git -C "$dir" pull origin "$BRANCH"
    else
        # create branch "marking" from "submission"; skip repo if "submission" doesn't exist
        if ! remote_ref_exists "$dir" "submission"; then
            echo "Branch/tag 'submission' not found on remote — skipping"
            continue
        fi
        echo "Creating new branch '$BRANCH' from 'submission'"
        run git -C "$dir" checkout submission
        run git -C "$dir" checkout -b "$BRANCH"
    fi

    ################################################################
    # 2. Stage everything needed (e.g., adding everything new in marking/)
    # 
    # THIS MAY NEED CHANGE!!!
    ################################################################
    # [[ -e "$dir/marking/simple" ]] && run git -C "$dir" mv marking/simple marking/01-slots-f1
    run git -C "$dir" add -f marking/

    ################################################################
    # 3. Commit and push!
    ################################################################
    run git -C "$dir" commit -m "$COMMIT_MESSAGE" || true   # true handles no changes to commit
    run git -C "$dir" push -u origin "$BRANCH"

    # if we are running just one case, exit after the first iteration
    $ONE_RUN && exit
    sleep "$TIME_SLEEP" # avoid hitting rate limits if pushing many repos in a row
done

echo
echo "Done. Processed $COUNTER submission(s)."



