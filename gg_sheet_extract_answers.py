"""
Issue marking comments to the Feedback PR of a student repo

Uses PyGithub (https://github.com/PyGithub/PyGithub) as API to GitHub:

    python3 -m pip install PyGithub

PyGithub documentation: https://pygithub.readthedocs.io/en/latest/introduction.html
Other doc on PyGithub: https://www.thepythoncode.com/article/using-github-api-in-python

Example:

$ python gh_pr_feedback_comment.py repos.csv marking.csv reports  -t ~/.ssh/keys/gh-token-ssardina.txt --repos s3975993 |& tee -a pr_feedback.log
"""

__author__ = "Sebastian Sardina & Andrew Chester - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2024-2025"

import csv
import os
from argparse import ArgumentParser
from typing import List
from datetime import datetime
from zoneinfo import ZoneInfo  # this should work Python 3.9+
from github import GithubException
import importlib.util
import sys
import time

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

import logging
import coloredlogs
LOGGING_LEVEL = logging.INFO
logger = logging.getLogger(__name__)
# logging.basicConfig(format=LOGGING_FMT, level=LOGGING_LEVEL, datefmt=LOGGING_DATE)
coloredlogs.install(
    logger=logger, level=LOGGING_LEVEL, fmt=LOGGING_FMT, datefmt=LOGGING_DATE
)


#####################################
# LOCAL GLOBAL VARIABLES FOR SCRIPT
#####################################
CSV_HEADER = ["REPO_ID_SUFFIX", "AUTHOR", "COMMITS", "ADDITIONS", "DELETIONS"]
CSV_ERRORS = "pr_comment_errors.csv"

SLEEP_RATE = 10  # number of repos to process before sleeping
SLEEP_TIME = 5  # sleep time in seconds between API calls

def load_marking_dict(file_path: str, col_key="GHU") -> dict:
    """
    Load the marking dictionary from a CSV file; keys are GH username
    """
    import pandas as pd
    import numpy as np

    # Old way to get a dictionary - does not regonise int type of columns
    # comment_dict = {}
    # with open(file_path, "r") as f:
    #     reader = csv.DictReader(f)
    #     for row in reader:
    #         comment_dict[row["GHU"].lower()] = row

    # Now we use Pandas as it recognizes column types (numbers)
    df = pd.read_csv(file_path)
    df.dropna(subset=[col_key], inplace=True)
    df.drop_duplicates(subset=[col_key], keep="last", inplace=True)
    df = df.replace(np.nan, "")
    df.set_index(col_key, inplace=True)
    df = df.round(2)
    comment_dict = df.to_dict(orient="index")
    for x in comment_dict:
        comment_dict[x][col_key] = x

    return comment_dict


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
    parser.add_argument("MARKING_CSV", help="List of student results.")
    parser.add_argument("REPORT_FOLDER", help="Folder containing student report files.")
    parser.add_argument(
        "CONFIG", help="Python file with the specific config for for assessment."
    )
    parser.add_argument(
        "--repos", nargs="+", help="if given, only the teams specified will be parsed."
    )
    parser.add_argument(
        "-t",
        "--token-file",
        help="File containing GitHub authorization token/password.",
    )
    parser.add_argument(
        "--extension",
        "-ext",
        default="txt",
        help="Extension of report file (Default: %(default)s).",
    )
    parser.add_argument(
        "--start",
        "-s",
        type=int,
        help="repo no to start processing from (starts in 1).",
    )
    parser.add_argument("--end", "-e", type=int, help="repo no to end processing.")
    parser.add_argument(
        "--no-report",
        action="store_true",
        default=False,
        help="Do not push the automarking report; just feedback result %(default)s.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Do not push to repos, just report on console %(default)s.",
    )
    args = parser.parse_args()

    now = datetime.now(TIMEZONE).isoformat()
    logger.info(f"Starting on {TIMEZONE}: {now}\n")

    # Now load the report feedback module for the specific assessment being used
    # Load the module from the given path
    # https://medium.com/@Doug-Creates/dynamically-import-a-module-by-full-path-in-python-bbdf4815153e
    spec = importlib.util.spec_from_file_location("module_name", args.CONFIG)
    module_feedback = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module_feedback)
    # Add the module to sys.modules
    sys.modules["module_name"] = module_feedback

    FEEDBACK_MESSAGE = getattr(module_feedback, "FEEDBACK_MESSAGE")
    report_feedback = getattr(module_feedback, "report_feedback")
    check_submission = getattr(module_feedback, "check_submission")

    # Get the list of relevant repos from the CSV file
    list_repos = util.get_repos_from_csv(args.REPO_CSV, args.repos)
    start_no = 1
    end_no = len(list_repos)
    if args.repos is None:
        start_no = args.start if args.start is not None else 0
        end_no = args.end if args.end is not None else len(list_repos)
        logger.info(f"Getting repos {start_no} to {end_no}")
        list_repos = list_repos[start_no - 1 : end_no]

    logger.info(args)

    if len(list_repos) == 0:
        logger.error(f'No repos found in the mapping file "{args.REPO_CSV}". Stopping.')
        exit(0)

    marking_dict = load_marking_dict(args.MARKING_CSV)

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
    for k, r in enumerate(list_repos):
        if k % SLEEP_RATE == 0 and k > 0:
            logger.info(f"Sleep for {SLEEP_TIME} seconds...")
            time.sleep(SLEEP_TIME)

        repo_no = r["NO"]
        repo_id = r["REPO_ID_SUFFIX"].lower()
        repo_name = r["REPO_ID"]
        # repo_url = f"https://github.com/{repo_name}"
        repo_url = r["REPO_HTTP"]
        logger.info(
            f"Processing repo {k+start_no}/{end_no}: {repo_id} - {repo_url}/pull/1"
        )
        if repo_id not in marking_dict:
            logger.error(f"\t Repo {repo_name} not found in {args.MARKING_CSV}.")
            errors.append([repo_id, repo_url, "Repo not found in marking CSV"])
            continue

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
                            f"\t Feedback PR found in number {pr.number}! Using this one: {repo_url}/pull/{pr.number}"
                        )
                        pr_feedback = repo.get_issue(number=pr.number)
                        break
                if pr_feedback is None:
                    logger.error("\t Feedback PR not found! Skipping...")
                    errors.append([repo_id, repo_url, "Feedback PR not found"])
                    continue

            # get the marking data for the student/repo
            marking_repo = marking_dict[repo_id]

            # print(marking_repo["Q3T"])
            # print(type(marking_repo["Q3T"]))
            # exit(0)

            # First, check the submission row: should we skip it for any reason?
            #   no certification, no submission, no marking, audit, etc..
            message, skip = check_submission(repo_id, marking_repo, logger)
            if message is not None:
                issue_feedback_comment(pr_feedback, message, args.dry_run)
            if skip:
                continue

            # Now there is a proper submission; issue the autograder report & feedback summary
            # create a new comment with the automarker report
            if not args.no_report:
                file_report = os.path.join(
                    args.REPORT_FOLDER, f"{repo_id}.{args.extension}"
                )  # default report filename
                file_report_error = os.path.join(
                    args.REPORT_FOLDER, f"{repo_id}_ERROR.{args.extension}"
                )  # default report filename
                if "REPORT" in marking_repo:
                    file_report = os.path.join(
                        args.REPORT_FOLDER, marking_repo["REPORT"]
                    )

                # if there is an error report, then use that one
                error_text = None
                if os.path.exists(file_report_error):
                    file_report = file_report_error
                    error_text = (
                        "Your solution seems non-error free as requested in spec... 🥴"
                    )

                if not os.path.exists(file_report):
                    logger.error(
                        f"\t Error in repo {repo_name}: report {file_report} (or _ERROR) not found."
                    )
                    errors.append([repo_id, repo_url, "Report not found"])
                    continue
                if os.stat(file_report).st_size > 50000:
                    logger.warning(f"\t Too large automarker report to publish")
                    issue_feedback_comment(
                        pr_feedback,
                        f"Too large automarker report to publish... 🥴",
                        args.dry_run,
                    )
                else:
                    # ok we have a good automarker report to publish now...
                    with open(os.path.join(file_report), "r") as report:
                        report_text = report.read()

                    message = f"# Full autograder report \n\n ```{args.extension}\n{report_text}```"
                    if error_text is not None:
                        message += f"\n**NOTE**: {error_text}"
                    message += f"\n{FEEDBACK_MESSAGE}"
                    issue_feedback_comment(pr_feedback, message, args.dry_run)

            # create a new comment with the final marking/feedback table results
            feedback_text = report_feedback(marking_repo)
            message = f"Dear @{repo_id}: find here the FEEDBACK & RESULTS for the project. \n\n {feedback_text}"
            issue_feedback_comment(pr_feedback, message, args.dry_run)
        except GithubException as e:
            logger.error(f"\t Error in repo {repo_name}: {e}")
            errors.append([repo_id, repo_url, e])
        except Exception as e:
            logger.error(f"\t Unknown error in repo {repo_name}: {e}")
            errors.append([repo_id, repo_url, e])

    logger.info(f"Finished! Total repos: {no_repos} - Errors: {len(errors)}.")

    with open(CSV_ERRORS, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["REPO_ID_SUFFIX", "REPO_URL", "ERROR"])
        writer.writerows(errors)

    logger.info(f"Repos with errors written to {CSV_ERRORS}.")
