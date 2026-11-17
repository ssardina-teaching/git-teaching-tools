"""
Transfer all issues from a GitHub repo A to another repo B, possibly in a different
organization.

GitHub can only transfer an issue between two repos that have the same owner
(GraphQL mutation transferIssue). To move issues across organizations, this script
uses a temporary "carrier" repo T:

    1. Create a temporary repo T in the owner of A (organization or user account).
    2. Transfer the issues A -> T (same owner, so allowed).
    3. Transfer the whole repo T to the owner of B (REST repo transfer);
       T keeps its issues when it changes owner.
    4. Transfer all issues T -> B (now same owner again).
    5. Delete T, but only if it has no issues left (so nothing is ever lost).

If A and B are in the same organization, issues are transferred A -> B directly and
no temporary repo is used.

If anything fails part way, the temporary repo is NOT deleted, and the script
reports where the issues currently are, so the transfer can be finished by hand
(or by re-running the script with T as the source).

What gets transferred:
    - Open issues only by default; use --closed to include closed issues as well.
    - Issue title, body, comments, assignees (if they have access to the target)
      and state are kept. Labels and milestones are kept only if they exist in
      the target repo (matched by name). Issue numbers change. Pull requests are
      never transferred. GitHub leaves a redirect from the old issue URL.

Requirements:
    - Admin access to A and B, and issues enabled in B (checked before starting).
    - Permission to create repos in A's owner (if a user account, it must be the
      authenticated user) and to transfer repos into B's owner.
    - A token with "repo" and "delete_repo" scopes (the latter to delete T).
    - GitHub does not allow moving issues from a private repo to a public one, so
      if A is private, B must be private too. T is given the same visibility as A.

Uses the GitHub GraphQL API to list and transfer issues, the REST API to transfer
the temporary repo, and PyGithub (https://github.com/PyGithub/PyGithub) for the
rest (repo checks, creation and deletion).

Examples:

    # preview what would happen, without changing anything
    $ python gh_issues_transfer.py org-2025/project-solution org-2026/project -t ~/.ssh/keys/gh-token.txt --dry-run

    # transfer open and closed issues
    $ python gh_issues_transfer.py org-2025/project-solution org-2026/project -t ~/.ssh/keys/gh-token.txt --closed
"""
__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2024-2026"

import argparse
import sys
import time
import traceback
from datetime import datetime
from typing import NoReturn

import requests
from github.GithubException import GithubException

import utils_gh
from util import parse_full_repo, TIMEZONE

# setup my own logger for this script, using the slogger/loguru backend
from slogger.loguru_backend import logger, setup_logger

SCRIPT_NAME = "gh_issues_transfer"
setup_logger(source=SCRIPT_NAME, timezone=TIMEZONE.key)

SLEEP_BETWEEN_TRANSFERS = 0.5  # seconds; avoids GitHub secondary rate limits
REPO_TRANSFER_TIMEOUT = 120  # seconds to wait for the temp repo to show up in dest org


# ==========================
# Helpers
# ==========================


def transfer_issue(issue_id: str, target_repo_id: str) -> str:
    """Transfer one issue (by node id) to a repo (by node id). Returns new issue URL."""
    mutation = """
    mutation($issueId: ID!, $repositoryId: ID!) {
      transferIssue(input: {issueId: $issueId, repositoryId: $repositoryId}) {
        issue { url }
      }
    }
    """
    result = utils_gh.run_query(
        mutation, {"issueId": issue_id, "repositoryId": target_repo_id}
    )
    return result["data"]["transferIssue"]["issue"]["url"]


def transfer_issues(source_full: str, target_full: str, closed: bool = False) -> int:
    """Transfer the issues of source_full to target_full (both 'org/repo', same owner).

    Only open issues unless closed=True. Returns the number of issues that FAILED to
    transfer (0 means everything was moved).
    """
    source_org, source_name = parse_full_repo(source_full)
    target_org, target_name = parse_full_repo(target_full)

    target_id = utils_gh.get_repository_node_id(target_org, target_name)
    issues = utils_gh.get_issues(source_org, source_name, closed=closed)

    if not issues:
        logger.info(f"No issues to transfer in {source_full}.")
        return 0

    logger.info(f"📋 Found {len(issues)} issues in {source_full}. Transferring to {target_full}...")
    failed = 0
    for issue in issues:
        logger.info(f"🔄 Issue #{issue['number']} ({issue['state']}): {issue['title']}")
        try:
            new_url = transfer_issue(issue["id"], target_id)
            logger.info(f"✅ Moved to {new_url}", depth=1)
        except Exception as e:
            failed += 1
            logger.error(f"❌ Failed: {e}", depth=1)
        time.sleep(SLEEP_BETWEEN_TRANSFERS)

    logger.info(f"Transferred {len(issues) - failed}/{len(issues)} issues {source_full} ---> {target_full}.")
    return failed


def transfer_repo(full_name: str, new_owner: str) -> None:
    """Transfer repo full_name to organization/user new_owner (REST API).
    https://docs.github.com/rest/repos/repos#transfer-a-repository
    """
    response = requests.post(
        f"https://api.github.com/repos/{full_name}/transfer",
        headers={
            "Authorization": f"token {utils_gh.TOKEN}",
            "Accept": "application/vnd.github+json",
        },
        json={"new_owner": new_owner},
    )
    if response.status_code not in (201, 202):
        raise RuntimeError(f"Repo transfer failed ({response.status_code}): {response.text}")


def wait_for_repo(gh, full_name: str, timeout: int = REPO_TRANSFER_TIMEOUT):
    """Poll until repo full_name is accessible (transfers are asynchronous)."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            return gh.get_repo(full_name)
        except GithubException:
            time.sleep(3)
    raise RuntimeError(f"Timeout after {timeout}s waiting for {full_name} to appear")


def abort(msg: str) -> NoReturn:
    logger.error(msg)
    sys.exit(1)


# ==========================
# Main
# ==========================


def main():
    parser = argparse.ArgumentParser(
        description="Transfer issues between GitHub repositories, also across organizations "
        "(via a temporary carrier repo)."
    )
    parser.add_argument("SOURCE_REPO", help="Source repository, as org/repo.")
    parser.add_argument("DEST_REPO", help="Destination repository, as org/repo.")
    parser.add_argument(
        "--closed",
        action="store_true",
        help="Transfer closed issues as well (default: only open issues).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list the issues and the plan; do not change anything.",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Do not ask for confirmation before starting.",
    )
    parser.add_argument(
        "--token", "-t",
        help="GitHub token, or file containing it (default: env GHTOKEN or GH_TOKEN).",
    )
    args = parser.parse_args()
    logger.info(args)

    source_full = args.SOURCE_REPO
    dest_full = args.DEST_REPO
    source_org, source_name = parse_full_repo(source_full)
    dest_org, _ = parse_full_repo(dest_full)
    same_org = source_org.lower() == dest_org.lower()

    ###############################################
    # Authenticate and sanity checks
    ###############################################
    try:
        gh = utils_gh.open_gitHub(token=args.token)
    except Exception:
        logger.error("Something went wrong during GitHub authentication. Check credentials.")
        traceback.print_exc()
        sys.exit(1)

    try:
        gh_source = gh.get_repo(source_full)
        gh_dest = gh.get_repo(dest_full)
    except GithubException as e:
        abort(f"Error accessing source/destination repositories: {e}")

    if gh_source.full_name.lower() == gh_dest.full_name.lower():
        abort("Source and destination repositories are the same.")
    if not gh_dest.has_issues:
        abort(f"Issues are not enabled in destination repo {dest_full}. "
              f"Enable them in Settings > General > Features, then re-run.")
    if gh_source.private and not gh_dest.private:
        abort(f"GitHub does not allow moving issues from private repo {source_full} "
              f"to public repo {dest_full}.")

    issues = utils_gh.get_issues(source_org, source_name, closed=args.closed)
    kind = "open and closed" if args.closed else "open"
    if not issues:
        logger.info(f"✅ No {kind} issues in {source_full}. Nothing to do.")
        return

    ###############################################
    # Show plan and confirm
    ###############################################
    temp_name = f"tmp-issue-transfer-{source_name}-{datetime.now(TIMEZONE):%Y%m%d%H%M%S}"
    logger.info(f"Plan: move {len(issues)} {kind} issues {source_full} ---> {dest_full}")
    if same_org:
        logger.info("Same organization: issues are transferred directly.", depth=1)
    else:
        visibility = "private" if gh_source.private else "public"
        logger.info(f"Via {visibility} temporary repo {source_org}/{temp_name}, "
                    f"which is moved to {dest_org} and deleted at the end.", depth=1)
    if not args.closed:
        logger.info("Closed issues will NOT be transferred (use --closed to include them).", depth=1)
    for issue in issues:
        logger.info(f"#{issue['number']} ({issue['state']}): {issue['title']}", depth=1)

    if args.dry_run:
        logger.info("Dry run: nothing changed.")
        return
    if not args.yes and input("Continue? (y/n): ").strip().lower() != "y":
        logger.warning("Aborting transfer.")
        return

    ###############################################
    # Same organization: direct transfer
    ###############################################
    if same_org:
        failed = transfer_issues(source_full, dest_full, closed=args.closed)
        if failed:
            abort(f"{failed} issues could not be transferred and remain in {source_full}.")
        logger.info("Issue transfer completed successfully. 🏆")
        return

    ###############################################
    # Different organizations: go via temporary repo T
    ###############################################
    # 1. Create T in source owner (same visibility as A, so issues can move A -> T -> B)
    #    The owner may be an organization or a user account (then it must be the
    #    authenticated user, as one cannot create repos in another user's account)
    try:
        if gh_source.owner.type == "Organization":
            gh_owner = gh.get_organization(source_org)
        else:
            gh_owner = gh.get_user()  # authenticated user (has create_repo)
            if gh_owner.login.lower() != source_org.lower():
                abort(f"Source repo is owned by user {source_org}, but authenticated as "
                      f"{gh_owner.login}; can only create the temporary repo in your own account.")
        gh_temp = gh_owner.create_repo(  # type: ignore[union-attr]
            name=temp_name, private=gh_source.private, auto_init=True
        )
    except GithubException as e:
        abort(f"Could not create temporary repo {source_org}/{temp_name}: {e}")
    logger.info(f"Created temporary repo {gh_temp.full_name}.")

    # 2. Transfer issues A -> T (failures simply stay in A)
    failed = transfer_issues(source_full, gh_temp.full_name, closed=args.closed)
    if failed:
        logger.warning(f"{failed} issues could not be moved and remain in {source_full}.")

    # 3. Transfer repo T to destination org
    logger.info(f"Transferring repo {gh_temp.full_name} to organization {dest_org}...")
    try:
        transfer_repo(gh_temp.full_name, dest_org)
        gh_temp = wait_for_repo(gh, f"{dest_org}/{temp_name}")
    except Exception as e:
        abort(f"{e}\nIssues are now in temporary repo {gh_temp.full_name}; "
              f"it was NOT deleted. Finish the transfer by hand.")

    # 4. Transfer ALL issues T -> B (everything in T came from A)
    failed = transfer_issues(gh_temp.full_name, dest_full, closed=True)

    # 5. Delete T only if it is empty, so no issue is ever lost
    left = utils_gh.get_issues(dest_org, temp_name, closed=True)
    if failed or left:
        abort(f"{len(left)} issues remain in temporary repo {gh_temp.full_name}; it was NOT deleted. "
              f"Re-run with it as source: python gh_issues_transfer.py {gh_temp.full_name} {dest_full} --closed")

    logger.info(f"Deleting temporary repo {gh_temp.full_name}.")
    try:
        gh_temp.delete()
    except GithubException as e:
        logger.warning(f"Could not delete temporary repo {gh_temp.full_name} (needs delete_repo scope?): {e}")
    logger.info("Issue transfer completed successfully. 🏆")


if __name__ == "__main__":
    main()
