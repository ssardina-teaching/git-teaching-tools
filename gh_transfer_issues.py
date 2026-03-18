"""
This script will transfer all issues from one repo A to another repo B

Repo A and B would not be in the same organization, but the user must have admin permissions to both repos. If they are in the same organization, then the transfer can be done directly via the GitHub UI, so this script is not needed.

The process is like this:

1. Create a temporary repo T in the same organization as A
2. Transfer all issues from A to T (this can be done via GraphQL API, as there is a specific mutation for this: https://docs.github.com/en/graphql/reference/mutations#transferissue)
3. Transfer repo T to the organization of B (this can be done via REST API, as there is a specific endpoint for this: https://docs.github.com/rest/repos/repos#transfer-a-repository)
4. Transfer all issues from T to B (same as step 2)
5. Delete repo T

Note: permissions required:
    - admin to both repos A and B to transfer issues
    - create repo permissions in both organizations to create the temporary repo T
    - admin permissions to the temporary repo T to transfer issues from T to B and to delete the temporary repo T at the end
    - delete_repo permissions in the token

This uses the GitHub GraphQL API, which is more efficient for transferring issues, as there are specific mutations for this. The REST API does not have specific endpoints for transferring issues, so it would require more complex logic to achieve the same result.

We use PyGithub (https://github.com/PyGithub/PyGithub) as API to GitHub to create the temp repo

Example:

$ python gh_transfer_issues.py  RMIT-COSC2780-2973-IDM25/project-exam-timetabling-solution RMIT-COSC2780-2973-IDM26/test -t ~/.ssh/keys/gh-token-ssardina.txt
"""

import argparse
import time
import requests
import gh_utils
from github.GithubException import GithubException

import logging
from slogger import setup_logging
import util
logger = setup_logging("transfer_repo", rotating_file="teaching.log", indent=2)
logger.setLevel(logging.INFO)  # set the level of the application logger
# logger.setLevel(logging.DEBUG)  # set the level of the application logger
logging.root.setLevel(logging.WARNING)  # root logger above info: no 3rd party logs


# ==========================
# Helpers
# ==========================

def transfer_issue(issue_id, target_repo_id):
    """Executes the transfer mutation for a single issue."""
    mutation = """
    mutation($issueId: ID!, $repositoryId: ID!) {
      transferIssue(input: {issueId: $issueId, repositoryId: $repositoryId}) {
        issue { url }
      }
    }
    """
    logger.debug(f"Running mutation to transfer issue {issue_id} to repo {target_repo_id} on mutation: {mutation}")
    return gh_utils.run_query(mutation, {"issueId": issue_id, "repositoryId": target_repo_id})


def transfer_issues(repo1, repo2, closed=False):
    org1, name1 = repo1.split("/")
    org2, name2 = repo2.split("/")

    # 1. Get IDs
    try:
        # repo1_id = gh_utils.get_repository_node_id(org1, name1)
        repo2_id = gh_utils.get_repository_node_id(org2, name2)
        issues = gh_utils.get_issues(org1, name1, closed=closed)
    except Exception as e:
        raise Exception(f"❌ Initialization of issue transferring failed: {e}")

    if not issues:
        logger.info(f"✅ No open issues found to transfer in repo {repo1}.")
        return

    logger.info(f"📋 Found {len(issues)} issues. Beginning transfer...")

    # 2. Loop and Transfer
    for issue in issues:
        try:
            logger.info(f"🔄 Transferring issue #{issue['number']}: {issue['title']}...")
            transfer_issue(issue['id'], repo2_id)
            logger.info("✅ Done!", depth=1)
            # Small sleep to avoid hitting secondary rate limits
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Failed! ❌\n   Error: {e}")

    logger.info("🎉 Bulk transfer complete.")


def wait_for_repo(gh, full_name, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            return gh.get_repo(full_name)
        except GithubException:
            time.sleep(2)
    raise RuntimeError(f"Timeout waiting for {full_name}")


# ==========================
# Main
# ==========================


def main():
    parser = argparse.ArgumentParser(
        description="Transfer issues between GitHub repositories across organizations"
    )
    parser.add_argument(
        "SOURCE_REPO", help="Source repository in format org/repo"
    )
    parser.add_argument(
        "DEST_REPO", help="Destination repository in format org/repo"
    )
    parser.add_argument(
        "--closed", action="store_true", help="Whether to transfer closed issues as well"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Run the script without making any changes (for testing)"
    )
    parser.add_argument(
        "--token-file", "-t", required=True, help="File containing GitHub token"
    )
    args = parser.parse_args()

    source_repo_full = args.SOURCE_REPO
    dest_repo_full = args.DEST_REPO
    source_org_name, source_repo_name = gh_utils.parse_full_repo(source_repo_full)
    dest_org_name, dest_repo_name = gh_utils.parse_full_repo(dest_repo_full)

    same_org = False
    if source_org_name == dest_org_name:
        same_org = True

    ###############################################
    # 0. Authenticate to GitHub
    ###############################################
    gh_token = util.read_token(args.token_file)
    gh_utils.TOKEN = gh_token  # Set the token for util functions
    HEADERS = {"Authorization": f"token {gh_token}"}

    if not args.token_file and not (args.user or args.password):
        logger.error("No authentication provided, quitting....")
        exit(1)
    try:
        gh = gh_utils.open_gitHub(token_file=args.token_file)
    except Exception:
        logger.error(
            "Something wrong happened during GitHub authentication. Check credentials."
        )
        exit(1)

    # not really needed.... but we can check if the repos exist and we have access to them before starting the transfer
    try:
        gh.get_repo(source_repo_full)
        gh.get_repo(dest_repo_full)
    except GithubException as e:
        logger.error(f"Error accessing source/destination repositories: {e}")
        exit(1)

    # we use a temp repo to transfer issues from
    #  if same org, then temp is just the source repo
    #  otherwise, create temp in source to get all issues, then transfer ownership to dest org, then transfer issues to dest repo, then delete temp
    if same_org:
        logger.info("Source and destination repos are in the same organization. No need for temporary repo.")
        gh_temp_repo = gh.get_repo(source_repo_full)
    else:
        # ==========================
        # 1. Create temporary repo in source org
        #   repo name will be "temp"
        # ==========================
        gh_source_org = gh.get_organization(source_org_name)

        try:
            # here we use PyGithub to create a temporary repo
            gh_temp_repo = gh_source_org.create_repo(
                name="temp", private=True, auto_init=True
            )
            logger.info(f"Created temporary repo {gh_temp_repo.full_name} for issue transfer.")
        except GithubException as e:
            logger.error(f"Error creating temp repo in source: {e}")
            gh_temp_repo = gh.get_repo(f"{source_org_name}/temp")
            logger.info(f"Using existing temporary repo {gh_temp_repo.full_name} for issue transfer.")
            # exit(1)

        # # ==========================
        # # 2. Transfer issues A -> T
        # # ==========================
        logger.info(f"Transferring ALL issues {args.SOURCE_REPO} ---> {gh_temp_repo.full_name}")
        transfer_issues(args.SOURCE_REPO, gh_temp_repo.full_name, closed=args.closed)

        # ==========================
        # 3. Transfer repo T to destination org
        # ==========================
        # easier and clearner to do via REST API than GraphQL, as there is a specific endpoint for this: https://docs.github.com/rest/repos/repos#transfer-a-repository
        logger.info(f"Transferring repo {gh_temp_repo.full_name} to organization {dest_org_name}")
        transfer_url = (
            f"https://api.github.com/repos/{source_org_name}/temp/transfer"
        )
        response = requests.post(
            transfer_url, headers=HEADERS, json={"new_owner": dest_org_name}
        )
        if response.status_code not in (202, 201):
            raise RuntimeError(f"Repo transfer failed: {response.text}")

        # Wait until repo appears in destination org
        gh_temp_repo = wait_for_repo(gh, f"{dest_org_name}/temp")

    # # ==========================
    # # 4. Transfer issues T -> B
    # # ==========================
    gh_repo_dest = gh.get_repo(dest_repo_full)

    logger.info(
        f"Transferring ALL issues in {gh_temp_repo.full_name} ---> {gh_repo_dest.full_name}"
    )
    transfer_issues(gh_temp_repo.full_name, gh_repo_dest.full_name, closed=True)

    # ==========================
    # 5. Delete temporary repo if was needed
    # ==========================
    if not same_org:
        logger.info("Deleting temporary repo")
        gh_temp_repo.delete()
        logger.info("Issue transfer completed successfully. 🏆")


if __name__ == "__main__":
    main()
