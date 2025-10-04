"""
Post a comment to the Feedback PR of a student repo.

This script does not require a marking CSV, just a repo CSV.
You cannot add text depending on marking info, like the commit processed or date of submission.
Script gh_pr_post_result.py uses marking CSV and is therefore more powerful

Uses PyGithub (https://github.com/PyGithub/PyGithub) as API to GitHub:

    python3 -m pip install PyGithub

PyGithub documentation: https://pygithub.readthedocs.io/en/latest/introduction.html
Other doc on PyGithub: https://www.thepythoncode.com/article/using-github-api-in-python

Example:

$ python gh_pr_post_comment.py -t ~/.ssh/keys/gh-token-ssardina.txt repos.csv message.py

message.py should have a string constant MESSAGE
"""
__author__ = "Sebastian Sardina & Andrew Chester - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2024-2025"
import csv
import os
from argparse import ArgumentParser
from pathlib import Path
import traceback
from typing import List
from datetime import datetime
from zoneinfo import ZoneInfo  # this should work Python 3.9+
from github import GithubException
import importlib.util
import sys
import time

import util
from util import (
    NOW_ISO,
    TIMEZONE,
    TIMEZONE_STR,
    UTC,
    NOW,
    NOW_TXT,
    LOGGING_DATE,
    LOGGING_FMT,
)
SCRIPT_NAME = "git_post_comment"

import logging
from slogger import setup_logging
logger = setup_logging(SCRIPT_NAME, rotating_file="app.log", indent=2)
logger.setLevel(logging.INFO)  # set the level of the application logger
logging.root.setLevel(logging.WARNING)  # root logger above info: no 3rd party logs

#####################################
# LOCAL GLOBAL VARIABLES FOR SCRIPT
#####################################

SLEEP_RATE = 10  # number of repos to process before sleeping
SLEEP_TIME = 5  # sleep time in seconds between API calls


def issue_feedback_comment(pr, message, dry_run=False):
    if dry_run:
        print("=" * 80)
        print(message)
        print("=" * 80)
    else:
        return pr.create_comment(message)


if __name__ == "__main__":
    parser = ArgumentParser(description="Merge PRs in multiple repos")
    parser.add_argument("REPO_CSV", help="List of repositories to post comments to.")
    parser.add_argument(
        "MESSAGE_FILE", help="File containing constant MESSAGE to post."
    )
    parser.add_argument(
        "-t",
        "--token-file",
        required=True,
        help="File containing GitHub authorization token/password.",
    )
    parser.add_argument(
        "--repos", nargs="+", help="if given, only the teams specified will be parsed."
    )
    parser.add_argument(
        "--ignore", nargs="+", help="if given, ignore these repos."
    )
    parser.add_argument(
        "--ghu",
        type=str,
        default="GHU",
        help="if given, only the submission specified will be parsed (Default: %(default)s).",
    )
    parser.add_argument(
        "--start",
        "-s",
        type=int,
        default=1,
        help="repo no to start processing from (Default: %(default)s).",
    )
    parser.add_argument("--end", "-e", type=int, help="repo no to end processing.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Do not push to repos, just report on console %(default)s.",
    )
    args = parser.parse_args()
    logger.info(f"Starting script {SCRIPT_NAME} on {TIMEZONE}: {NOW_ISO}")
    logger.info(args, depth=1)

    if not os.path.isfile(args.REPO_CSV):
        logger.error(f"Repo CSV file {args.REPO_CSV} not found.")
        exit(1)

    if not os.path.isfile(args.MESSAGE_FILE):
        logger.error(f"Message file {args.MESSAGE_FILE} not found.")
        exit(1)

    ###############################################
    # Load feedback report builder module and marking spreadsheet
    # https://medium.com/@Doug-Creates/dynamically-import-a-module-by-full-path-in-python-bbdf4815153e
    ###############################################
    spec = importlib.util.spec_from_file_location("module_name", args.MESSAGE_FILE)
    module_feedback = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module_feedback)
    # Add the module to sys.modules
    sys.modules["module_name"] = module_feedback

    # get the message to post
    MESSAGE = getattr(module_feedback, "MESSAGE")
    get_repos = getattr(module_feedback, "get_repos")

    ###############################################
    # Filter repos as desired
    ###############################################
    list_repos = util.get_repos_from_csv(
        args.REPO_CSV, args.repos if args.repos is not None else get_repos(), args.ignore
    )
    if args.repos is None:
        end_no = args.end if args.end is not None else len(list_repos)
        list_repos = list_repos[args.start - 1 : end_no]

    if len(list_repos) == 0:
        logger.error(f'No relevant repos found in the mapping file "{args.REPO_CSV}". Stopping.')
        exit(0)

    logger.info(f'Number of relevant repos found: {len(list_repos)}')

    ###############################################
    # Authenticate to GitHub
    ###############################################
    if not args.token_file:
        logger.error("No token file for authentication provided, quitting....")
        exit(1)
    try:
        g = util.open_gitHub(token_file=args.token_file)
    except:
        logger.error(
            "Something wrong happened during GitHub authentication. Check credentials."
        )
        exit(1)

    ###############################################
    # Process each repo in list_repos
    ###############################################
    authors_stats = []
    no_repos = len(list_repos)
    errors = []
    for k, r in enumerate(list_repos, start=1):
        if k % SLEEP_RATE == 0 and k > 0:
            logger.info(f"Sleep for {SLEEP_TIME} seconds...")
            time.sleep(SLEEP_TIME)

        repo_no = r["NO"]
        repo_id = r["REPO_ID_SUFFIX"].lower()
        repo_name = r["REPO_ID"]
        repo_url = r["REPO_HTTP"]
        logger.info(
            f"Processing repo {k}/{no_repos}: {repo_no}:{repo_id} ({repo_url})..."
        )

        repo = g.get_repo(repo_name)
        try:
            # Find the Feedback PR - feedback
            #   see we cannot use .get_pull(1) bc it involves reviewing the PRs!
            pr_feedback = repo.get_issue(number=1)
            if pr_feedback.title != "Feedback":
                pr_feedback = None
                for pr in repo.get_pulls():
                    if pr.title == "Feedback":
                        logger.warning(
                            f"Feedback PR found in number {pr.number}! Using this one: {repo_url}/pull/{pr.number}", depth=1
                        )
                        pr_feedback = repo.get_issue(number=pr.number)
                        break
                if pr_feedback is None:
                    logger.error("\t Feedback PR not found! Skipping...")
                    errors.append([repo_id, repo_url, "Feedback PR not found"])
                    continue
            logger.debug(f"Feedback PR found: {pr_feedback}", depth=1)

            issue_feedback_comment(
                pr_feedback, MESSAGE.format(ghu=repo_id), args.dry_run
            )
            if not args.dry_run:
                logger.info(f"Message posted to {pr_feedback.html_url}.", depth=1)
        except GithubException as e:
            logger.error(f"Error in repo {repo_name}: {e}", depth=1)
            errors.append([repo_id, repo_url, e])
        except Exception as e:
            logger.error(
                f"Unknown error in repo {repo_name}: {e} \n {traceback.format_exc()}", depth=1
            )
            errors.append([repo_id, repo_url, e])

    logger.info(f"Finished! Total repos: {no_repos} - Errors: {len(errors)}.")
