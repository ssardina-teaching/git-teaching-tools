"""
Unsubscribe from a PR or issue

We do it with the issue node id and a GraphQL mutations, since the REST API does not allow to unsubscribe from a PR/issue, but only from a notification thread, which will only exist when a message has been posted (which means I will still get the first message!)

So we first get the node-id of the issue/PR via the REST API and PyGitHub, and then we execute the unsubscribe mutation in GraphQL.

* Uses PyGithub (https://github.com/PyGithub/PyGithub) as API to GitHub:
* PyGithub documentation: https://pygithub.readthedocs.io/en/latest/introduction.html
* GitHub REST API: https://docs.github.com/en/rest
* GitHub GraphQL API: https://docs.github.com/en/graphql
"""
__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com  + ChatGPT friend"
__copyright__ = "Copyright 2026"

from argparse import ArgumentParser
import traceback
from typing import List

# https://pygithub.readthedocs.io/en/latest/introduction.html
from github import Github, Repository, Organization, GithubException

import util, utils_gh
from util import (
    TIMEZONE,
    NOW_ISO,
    GH_HTTP_URL_PREFIX,
)


SCRIPT_NAME = "gh_unsubscribe"
SCRIPT_DESC = "Unsubscribe from notifications for a given PR or issue in multiple repos."


# setup my own logger for this script, using the slogger/loguru backend
from slogger.loguru_backend import logger, setup_logger

setup_logger(source=SCRIPT_NAME, timezone=TIMEZONE.key)


if __name__ == "__main__":
    parser = ArgumentParser(description=SCRIPT_DESC)
    parser.add_argument("REPO_CSV", help="List of repositories to get data from.")
    parser.add_argument(
        "--repos", nargs="+", help="if given, only the teams specified will be parsed."
    )
    parser.add_argument("--start", type=int, help="repo no to start processing from.")
    parser.add_argument("--end", type=int, help="repo no to end processing.")
    parser.add_argument("--no", type=int, help="number of the PR to merge.")
    parser.add_argument("--title", help="title of PR to merge.")
    parser.add_argument(
        "-t",
        "--token",
        # default=os.environ.get("GHTOKEN") or os.environ.get("GH_TOKEN"),
        help="File or string containing GitHub authorization token/password.",
    )
    args = parser.parse_args()
    logger.info(f"Starting script {SCRIPT_NAME} on {TIMEZONE}: {NOW_ISO}")
    logger.info(args, indent=1)

    pr_number = args.no
    pr_title = args.title

    if pr_number is None and pr_title is None:
        logger.error("You must provide a PR number or title to merge.")
        exit(1)

    # Get the list of TEAM + GIT REPO links from csv file
    list_repos = util.get_repos_from_csv(args.REPO_CSV, args.repos)

    if len(list_repos) == 0:
        logger.error(
            f'No repos found in the mapping file "{args.REPO_CSV}". Stopping.'
        )
        exit(0)
    if args.end is not None and args.end < len(list_repos):
        list_repos = list_repos[: args.end]

    ###############################################
    # Authenticate to GitHub
    ###############################################
    try:
        g = utils_gh.open_gitHub(token=args.token)
    except Exception as e:
        logger.error(
            "Something wrong happened during GitHub authentication. Check credentials."
        )
        traceback.print_exc()
        exit(1)

    ###############################################
    # Process each repo in list_repos
    ###############################################
    authors_stats = []
    no_repos = len(list_repos)
    no_unsubscribed = 0
    no_errors = 0
    for k, r in enumerate(list_repos, start=1):
        if args.start is not None and k < args.start:
            continue
        repo_id = r["REPO_ID_SUFFIX"]
        repo_name = r["REPO_ID"]
        repo_url = f"{GH_HTTP_URL_PREFIX}/{repo_name}"
        logger.info(f"Processing repo {k}/{no_repos}: {repo_id} ({repo_url})...")

        # get the repo object
        repo = g.get_repo(repo_name)

        pr_url = f"{repo_url}/pull/{pr_number}"

        issue_node_id = utils_gh.get_issue_node_id(g, repo, pr_number)
        if issue_node_id is None:
            logger.warning(f"PR {pr_number} not found in repo {repo_name}. Skipping.", indent=2)
            no_errors += 1
            continue

        logger.info(f"Found node id for PR {pr_number}: {issue_node_id} - {pr_url}", indent=2)
        data = utils_gh.unsubscribe(g, issue_node_id)
        logger.info(f"Unsubscribed from PR {pr_number}: {data}", indent=2)
        no_unsubscribed += 1

    logger.info(
        f"Finished! Total repos: {no_repos} - Unsubscribed successfully: {no_unsubscribed} - Failed to unsubscribe: {no_errors}."
    )
