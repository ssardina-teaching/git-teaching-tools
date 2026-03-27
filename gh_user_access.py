"""
Script to manage automarking/feedback workflows, like the ones used in GH Classroom

Uses PyGithub (https://github.com/PyGithub/PyGithub) as API to GitHub:

    python3 -m pip install PyGithub

PyGithub documentation: https://pygithub.readthedocs.io/en/latest/introduction.html

Library uses REST API: https://docs.github.com/en/rest

Some usage help on PyGithub:
    https://www.thepythoncode.com/article/using-github-api-in-python

Example:

    $ python ../../tools/git-hw-submissions.git/gh_workflow.py -t ~/.ssh/keys/gh-token-ssardina.txt \
        --name Autograding --until 2025-04-08T12:00 --run-name "Automarking up April 8 12pm" -- \
            start repos.csv |& tee -a autograde-2025-04-08T1200.log
"""
__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2024-2025"
import csv
import os
from argparse import ArgumentParser
import time
import util, utils_gh

# https://pygithub.readthedocs.io/en/latest/introduction.html
from github import Github, Repository, Organization, GithubException, Workflow
from util import (
    TIMEZONE,
    UTC,
    NOW,
    NOW_ISO,
    NOW_TXT,
    LOGGING_DATE,
    LOGGING_FMT,
    GH_HTTP_URL_PREFIX,
)

from datetime import datetime

import logging
import coloredlogs
LOGGING_LEVEL = logging.INFO
# LOGGING_LEVEL = logging.DEBUG
# logger.basicConfig(format=LOGGING_FMT, level=LOGGING_LEVEL, datefmt=LOGGING_DATE)
logger = logging.getLogger(__name__)
coloredlogs.install(level=LOGGING_LEVEL, fmt=LOGGING_FMT, datefmt=LOGGING_DATE)

OUTPUT_CSV = f"org-repos-{NOW_TXT}.csv"
OUTPUT_HEADER_CSV = ["REPO", "REPO_HTML", "USER", "PERMISSION"]
IGNORE_USERS = ["ssardina", "scott-robshaw", "axelahmer", "gourdoni"]

SLEEP_RATE = 10  # number of repos to process before sleeping
SLEEP_TIME = 5  # sleep time in seconds between API calls


if __name__ == "__main__":
    parser = ArgumentParser(description="Handle automarking workflows")
    parser.add_argument(
        "ACTION",
        choices=["list", "delete", "remove"],
        help="Action to do on workflows.",
    )
    parser.add_argument("ORG", help="GH Organization.")
    parser.add_argument("USER", help="GH username.")
    parser.add_argument(
        "-t",
        "--token-file",
        required=True,
        help="File containing GitHub authorization token/password.",
    )
    parser.add_argument(
        "--start",
        "-s",
        type=int,
        default=1,
        help="First repo to start with. Default %(default)s.",
    )
    parser.add_argument(
        "--end",
        "-e",
        type=int,
        help="Last repo to parse.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Do not push to repos, just report on console %(default)s.",
    )
    args = parser.parse_args()
    logger.info(f"Starting script on {TIMEZONE}: {NOW_ISO} - {args}")

    ###############################################
    # Authenticate to GitHub
    ###############################################
    if not args.token_file and not (args.user or args.password):
        logger.error("No authentication provided, quitting....")
        exit(1)
    try:
        g = utils_gh.open_gitHub(token_file=args.token_file)
    except Exception:
        logger.error(
            "Something wrong happened during GitHub authentication. Check credentials."
        )
        exit(1)

    # Get the org and user
    org = g.get_organization(args.ORG)
    user = g.get_user(args.USER)
    start = args.start

    repos_with_write = []

    # Loop through org repos and enumerate( user's permission
    repos = org.get_repos()
    repos_count = repos.totalCount
    end = args.end if args.end is not None else repos_count
    logger.info(f"Number of repo found in org {org.login}: {repos_count} - Parsing {start} to {end}")
    for k, repo in enumerate(repos[start-1:end], start=start):
        # Sleep to avoid hitting API limits
        if k % SLEEP_RATE == 0:
            logger.info(f"Sleeping for {SLEEP_TIME} seconds...")
            time.sleep(SLEEP_TIME)
        try:
            logger.info(f"Processing repo {k}/{repos_count}: {repo.name}")
            for u in repo.get_collaborators():
                if u.login in IGNORE_USERS:
                    continue
                u_perm = repo.get_collaborator_permission(u)
                repos_with_write.append([repo.full_name, repo.html_url, u.login, u_perm])
                logger.info(
                    f"\t User {u.login} has {u_perm} access to {repo.full_name}"
                )
        except Exception as e:
            # Might throw if you don’t have access to check perms
            logger.error(f"Skipping {repo.full_name}: {e}")

    # Write to CSV
    with open(OUTPUT_CSV, "w") as csvfile:
        writer = csv.writer(csvfile, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(OUTPUT_HEADER_CSV)
        for row in repos_with_write:
            writer.writerow(row)
