"""
Get the commits done after a given date in a list of repositories.

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
from argparse import ArgumentParser
import time
from datetime import datetime
import util
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
# https://pygithub.readthedocs.io/en/latest/introduction.html
from github import Github, Repository, Organization, GithubException, Workflow

import logging
import coloredlogs
LOGGING_LEVEL = logging.INFO
# LOGGING_LEVEL = logger.DEBUG
# logger.basicConfig(format=LOGGING_FMT, level= LOGGING_LEVEL, datefmt=LOGGING_DATE)
logging.Formatter.converter = util.timezone_time
logger = logging.getLogger(__name__)
coloredlogs.install(level=LOGGING_LEVEL, fmt=LOGGING_FMT, datefmt=LOGGING_DATE)

OUT_CSV = f"late-commits-{NOW_TXT}.csv"

SLEEP_RATE = 10  # number of repos to process before sleeping
SLEEP_TIME = 5  # sleep time in seconds between API calls


if __name__ == "__main__":
    parser = ArgumentParser(description="Handle automarking workflows")
    parser.add_argument("REPO_CSV", help="List of repositories to get data from.")
    parser.add_argument(
        "--repos", nargs="+", help="if given, only the teams specified will be parsed."
    )
    parser.add_argument(
        "-t",
        "--token-file",
        required=True,
        help="File containing GitHub authorization token/password.",
    )
    parser.add_argument(
        "--until",
        type=str,
        help="Get commit before this date. Datetime in ISO format, e.g., 2025-04-09T15:30. Overrides --commit.",
    )
    parser.add_argument(
        "--since",
        required=True,
        type=str,
        help="Get commits after this this date. Datetime in ISO format, e.g., 2025-04-09T15:30. Overrides --commit.",
    )
    parser.add_argument(
        "--ignore",
        nargs='+',
        type=str,
        default=[],
        help="Authors to ignore (Default: %(default)s).",
    )
    parser.add_argument(
        "--start",
        "-s",
        type=int,
        default=1,
        help="repo no to start processing from (Default: %(default)s).",
    )
    parser.add_argument("--end", "-e", type=int, help="repo no to end processing.")
    args = parser.parse_args()
    logger.info(f"Starting script on {TIMEZONE}: {NOW_ISO}")

    ###############################################
    # Filter repos as desired
    ###############################################
    # Get the list of TEAM + GIT REPO links from csv file
    repos = util.get_repos_from_csv(args.REPO_CSV, args.repos)
    if args.repos is None:
        end_no = args.end if args.end is not None else len(repos)
        repos = repos[args.start - 1 : end_no]

    if len(repos) == 0:
        logger.error(f'No repos found in the mapping file "{args.REPO_CSV}". Stopping.')
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
    until_dt = NOW
    if args.until is not None:
        until_dt = datetime.fromisoformat(args.until)
        if until_dt.tzinfo is None:
            until_dt = until_dt.replace(tzinfo=TIMEZONE)
    if args.since is not None:
        since_dt = datetime.fromisoformat(args.since)
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=TIMEZONE)
    logger.info(
        f"Getting commits between from {since_dt.isoformat()} until {until_dt.isoformat()}"
    )

    no_repos = len(repos)
    output_csv = []
    no_found = 0
    for k, r in enumerate(repos, start=1):
        if k % SLEEP_RATE == 0 and k > 0:
            logger.info(f"Sleep for {SLEEP_TIME} seconds...")
            time.sleep(SLEEP_TIME)

        # get the current repo data
        repo_no = r["NO"]
        repo_id = r["REPO_ID_SUFFIX"]
        repo_name = r["REPO_ID"]
        repo_url = f"{GH_HTTP_URL_PREFIX}/{repo_name}"
        logger.info(
            f"Processing repo {k}/{no_repos}: {repo_no}:{repo_id} ({repo_url})..."
        )
        repo = g.get_repo(repo_name)

        # first we get the workflow we are after
        commits = repo.get_commits(since=since_dt.astimezone(UTC))
        no_late = 0
        for c in commits:
            login = c.author.login
            found = False
            if not login in args.ignore:
                logger.info(
                    f"\t Found commit {c.sha} - '{c.commit.message}' - {login} - {c.commit.author.date.astimezone(TIMEZONE)}"
                )
                no_late += 1
        if no_late > 0:
            no_found += 1
            # get the very last commit that was legal (before deadline)
            last_valid_commit = repo.get_commits(until=since_dt.astimezone(UTC))[0]
            last_valid_commit_time = last_valid_commit.commit.author.date.astimezone(TIMEZONE)
            last_valid_commit_sha = last_valid_commit.sha
            last_valid_commit_message = last_valid_commit.commit.message
            last_valid_commit_url = f"{repo.html_url}/commit/{last_valid_commit_sha}"
            logger.info(f"Last valid commit: {last_valid_commit_sha} - '{last_valid_commit_message}' - {last_valid_commit_time} - {last_valid_commit_url}")
            output_csv.append(
                {
                    "REPO_ID_SUFFIX": repo_id,
                    "AUTHOR": login,
                    "URL": f"{repo.html_url}/commits/",
                    "NO_LATE": no_late,
                    "LAST_VALID_COMMIT": last_valid_commit_sha,
                    "LAST_VALID_COMMIT_TIME": last_valid_commit_time.isoformat(),
                    "LAST_VALID_COMMIT_MESSAGE": last_valid_commit_message,
                    "LAST_VALID_COMMIT_URL": last_valid_commit_url
                }
            )
    # Write output_csv to a CSV file
    with open(OUT_CSV, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=[
                "REPO_ID_SUFFIX",
                "AUTHOR",
                "URL",
                "NO_LATE",
                "LAST_VALID_COMMIT",
                "LAST_VALID_COMMIT_TIME",
                "LAST_VALID_COMMIT_MESSAGE",
                "LAST_VALID_COMMIT_URL",
            ],
            # delimiter="\t",
            quoting=csv.QUOTE_NONNUMERIC,
        )
        writer.writeheader()
        writer.writerows(output_csv)
    logger.info(
        f"Finished! No of repos processed: {no_repos} - Found: {no_found} - Output written to {OUT_CSV}"
    )
