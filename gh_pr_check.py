"""
Check correctness of Feedback PR:

    - is it missing?
    - has it been wrongly merged?
    - has there been a forced pushed reported?

This is useful to handle the Feedeback PRs #1 from GitHub Classroom, where students are supposed to fix their code

Uses PyGithub (https://github.com/PyGithub/PyGithub) as API to GitHub:

    python3 -m pip install PyGithub

PyGithub documentation: https://pygithub.readthedocs.io/en/latest/introduction.html
Other doc on PyGithub: https://www.thepythoncode.com/article/using-github-api-in-python
"""
__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2024-2025"

import csv
from argparse import ArgumentParser
import os

# https://pygithub.readthedocs.io/en/latest/introduction.html
from github import Github, Repository, Organization, GithubException

import util
from util import (
    TIMEZONE,
    UTC,
    NOW,
    NOW_ISO,
    NOW_TXT,
    LOGGING_DATE,
    LOGGING_FMT,
    GH_HTTP_URL_PREFIX,
    backup_file
)
SCRIPT_NAME = os.path.basename(__file__)

import logging
from slogger import setup_logging
logger = setup_logging(SCRIPT_NAME, rotating_file="app.log", timezone=TIMEZONE, indent=2)
logger.setLevel(logging.INFO)  # set the level of the application logger
logging.root.setLevel(logging.WARNING)  # root logger above info: no 3rd party logs


# Application global variables
CSV_HEADER = ["REPO_ID_SUFFIX", "REPO_ID", "PR_URL", "RESULT", "DETAILS"]
CSV_CHECK = "pr_check.csv"


if __name__ == "__main__":
    parser = ArgumentParser(description="Check PRs: missing, merged, forced pushed")
    parser.add_argument("REPO_CSV", help="List of repositories to get data from.")
    parser.add_argument(
        "-t",
        "--token-file",
        help="File containing GitHub authorization token/password.",
    )
    parser.add_argument(
        "--repos", nargs="+", help="if given, only the teams specified will be parsed."
    )
    parser.add_argument("--no", type=int, help="number of the PR to merge.")
    parser.add_argument("--title", help="title of PR to merge.")
    args = parser.parse_args()
    logger.info(f"Starting script {SCRIPT_NAME} on {TIMEZONE}: {NOW_ISO}")
    logger.info(args, depth=1)

    if args.no is None and args.title is None:
        logger.error("You must provide a PR number or title to merge.")
        exit(1)

    # Get the list of TEAM + GIT REPO links from csv file
    list_repos = util.get_repos_from_csv(args.REPO_CSV, args.repos)

    if len(list_repos) == 0:
        logger.error(
            f'No repos found in the mapping file "{args.REPO_CSV}". Stopping.'
        )
        exit(0)

    ###############################################
    # Authenticate to GitHub
    ###############################################
    if not args.token_file and not (args.user or args.password):
        logger.error("No authentication provided, quitting....")
        exit(1)
    try:
        g = util.open_gitHub(token_file=args.token_file)
    except Exception:
        logger.error(
            "Something wrong happened during GitHub authentication. Check credentials."
        )
        exit(1)

    ###############################################
    # Process each repo in list_repos
    ###############################################
    authors_stats = []
    no_repos = len(list_repos)
    rows_csv = []
    for k, r in enumerate(list_repos, start=1):
        row = r["REPO_ID_SUFFIX"]
        repo_name = r["REPO_ID"]
        repo_url = r["REPO_HTTP"]
        logger.info(f"Processing repo {k}/{no_repos}: {row} ({repo_url})...")

        repo = g.get_repo(repo_name)
        prs = repo.get_pulls(state="all", direction="desc")

        pr_selected = None
        try:
            if args.no is not None:
                if prs.totalCount < args.no:
                    logger.error(
                        f"No PR with number {args.no} - Repo has only {prs.totalCount} PRs.", depth=1
                    )
                    rows_csv.append([row, repo_name, "", "missing", args.no])
                    continue
                else:
                    pr_selected = repo.get_pull(args.no)
            else:
                for pr in prs:
                    logger.debug(f"PR: {pr.number} - {pr.title}", depth=1)
                    if args.title in pr.title:
                        pr_selected = pr
                        break
                if pr_selected is None:
                    logger.error(f"No PR containing '{args.title}' in title.", depth=1)
                    rows_csv.append([row, repo_name, "", "missing", args.title])
                    continue
            logger.info(f"Found relevant PR: {pr_selected}", depth=1)

            if pr_selected.merged:
                pr_url = f"{repo_url}/pull/{pr_selected.number}"
                logger.warning(f"PR Feedback merged!!! {pr_selected} - URL: {pr_url}", depth=1)
                rows_csv.append([row, repo_name, pr_url, "merged", ""])

            # check for forced push
            for event in pr_selected.get_issue_events():
                if event.event == "head_ref_force_pushed":
                    pr_url = f"{repo_url}/pull/{pr_selected.number}"
                    logger.warning(f"PR Feedback forcec pushed!!! {pr_selected} - actor: {event.actor} - URL: {pr_url}", depth=1)
                    rows_csv.append(
                        [row, repo_name, pr_url, "push_forced", event.actor]
                    )
                    break
        except GithubException as e:
            logger.error(f"Error in repo {repo_name}: {e}", depth=1)
            rows_csv.append([row, repo_name, pr_url, "error", e])

    logger.info(
        f"Finished! Total repos: {no_repos} - Problems: {len(rows_csv)} - Errors: {len([r for r in rows_csv if r[3] == 'error'])}."
    )

    # Finally, write data to CSV file
    backup_file(CSV_CHECK)
    rows_csv.sort()
    with open(CSV_CHECK, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_HEADER)
        writer.writerows([row for row in rows_csv])
    logger.info(f"Problematic PRs data written to {CSV_CHECK}.")
