"""
Script to merge a PR in all the repositories from a GitHub Classroom

Uses PyGithub (https://github.com/PyGithub/PyGithub) as API to GitHub:

    python3 -m pip install PyGithub

PyGithub documentation: https://pygithub.readthedocs.io/en/latest/introduction.html

Library uses REST API: https://docs.github.com/en/rest

Some usage help on PyGithub:
    https://www.thepythoncode.com/article/using-github-api-in-python
"""
__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2019-2026"

from argparse import ArgumentParser
from typing import List

# https://pygithub.readthedocs.io/en/latest/introduction.html
from github import Github, Repository, Organization, GithubException

import util, utils_gh
from util import (
    TIMEZONE,
    UTC,
    NOW,
    NOW_TXT,
    NOW_ISO,
    LOGGING_DATE,
    LOGGING_FMT,
    GH_HTTP_URL_PREFIX,
)
from datetime import datetime

SCRIPT_NAME = "git_merge_pr"
import logging
from slogger import setup_logging
logger = setup_logging(SCRIPT_NAME, rotating_file="app.log", timezone=TIMEZONE, indent=2)
logger.setLevel(logging.INFO)  # set the level of the application logger
logger.root.setLevel(logging.WARNING)  # root logger above info: no 3rd party logs


if __name__ == "__main__":
    parser = ArgumentParser(description="Merge PRs in multiple repos")
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
        "--token-file",
        required=True,
        help="File containing GitHub authorization token/password.",
    )
    args = parser.parse_args()
    logger.info(f"Starting script {SCRIPT_NAME} on {TIMEZONE}: {NOW_ISO}")
    logger.info(args, depth=1)

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
    if not args.token_file and not (args.user or args.password):
        logger.error("No authentication provided, quitting....")
        exit(1)
    try:
        g = utils_gh.open_gitHub(token_file=args.token_file)
    except Exception as e:
        logger.error(
            f"Something wrong happened during GitHub authentication. Check credentials. Exception: {e}"
        )
        exit(1)

    ###############################################
    # Process each repo in list_repos
    ###############################################
    authors_stats = []
    no_repos = len(list_repos)
    no_merged = 0
    no_errors = 0
    for k, r in enumerate(list_repos, start=1):
        if args.start is not None and k < args.start:
            continue
        repo_id = r["REPO_ID_SUFFIX"]
        repo_name = r["REPO_ID"]
        repo_url = f"{GH_HTTP_URL_PREFIX}/{repo_name}"
        logger.info(f"Processing repo {k}/{no_repos}: {repo_id} ({repo_url})...")

        repo = g.get_repo(repo_name)
        prs = repo.get_pulls(state="all", direction="desc")

        pr_selected = None
        if pr_number is not None:
            if prs.totalCount < pr_number:
                logger.error(
                    f"No PR with number {pr_number} - Repo has only {prs.totalCount} PRs.", depth=1
                )
                exit(1)
            else:
                pr_selected = repo.get_pull(pr_number)
        else:
            for pr in prs:
                if pr_title in pr.title:
                    pr_selected = pr
                    break
            if pr_selected is None:
                logger.warning(f"No PR containing '{pr_title}' in title.", depth=1)
                continue

        logger.info(f"Found relevant PR: {pr_selected}", depth=1)

        if pr_selected.merged:
            logger.info("PR already merged.", depth=1)
            continue

        logger.info(f"PR is still not merged - will try to merge it: {pr_selected}", depth=1)
        try:
            status = pr_selected.merge(merge_method="merge")
            if status.merged:
                logger.info("Successful merging...", depth=1)
                no_merged += 1
            else:
                logger.error(f"MERGING DIDN'T WORK - STATUS: {status}", depth=1)
                no_errors += 1
        except GithubException as e:
            logger.error(f"MERGING FAILED WITH EXCEPTION: {e}", depth=1)
            no_errors += 1

    logger.info(
        f"Finished! Total repos: {no_repos} - Merged successfully: {no_merged} - Failed to merge: {no_errors}."
    )
