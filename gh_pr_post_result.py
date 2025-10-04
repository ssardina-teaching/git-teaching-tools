"""
This script allows to post to repos Feedback PRs to send bulk messages or post results

Uses PyGithub (https://github.com/PyGithub/PyGithub) as API to GitHub:

    python3 -m pip install PyGithub

PyGithub documentation: https://pygithub.readthedocs.io/en/latest/introduction.html
Other doc on PyGithub: https://www.thepythoncode.com/article/using-github-api-in-python


The script is able to post:

1. post automarker reports (from file) with feedback text in a message
2. post a feedback summary message after the report message

By using 2 only, one can also use it to just post messages to the Feedback PR.
(e.g., clarify which commit was processed, or date of submission)

The script requires:

1. a CSV file with all the repos to process
2. a CSV file with the marking information (e.g., GHU, GH suffix, marks, feedback, etc.)
3. a Python file with the report builder configuration
3. [OPTIONAL] a folder with the automarker reports to be posted
4. The GH authorization token/password file (-t)

Example:

$ python ../tools/git-teaching-tools.git/gh_pr_post_result.py repos.csv marking.csv feedback_p2.py reports -t ~/.ssh/keys/gh-token-ssardina.txt --repos ssardina
 
The feedback builder (file pr_message.py in the example) must define the following functions:

- report_feedback(mapping): function to generate the feedback message
- check_submission(repo_id, mapping, logger): function to check if the repo should be processed
- FEEDBACK_MESSAGE: message to be added at the end of the feedback report
- get_repos() [OPTIONAL]: function to get the list of repos to process

The `mapping` is a dictionary with the marking information for the repo, representing one row of the CSV file.

For example on feedback builders see feedback_p2.py in this folder
"""
__author__ = "Sebastian Sardina & Andrew Chester - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2024-2025"
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
    UTC,
    NOW,
    NOW_TXT,
    LOGGING_DATE,
    LOGGING_FMT,
    add_csv
)
SCRIPT_NAME = "pr_post_result"

import logging
from slogger import setup_logging
logger = setup_logging(SCRIPT_NAME, rotating_file="app.log", indent=2)
logger.setLevel(logging.INFO)  # set the level of the application logger
logging.root.setLevel(logging.WARNING)  # root logger above info: no 3rd party logs


#####################################
# LOCAL GLOBAL VARIABLES FOR SCRIPT
#####################################
CSV_ERRORS = "pr_comment_errors.csv"
CSV_ERRORS_HEADER = ["REPO_ID_SUFFIX", "REPO_URL", "ERROR"]

CSV_POSTED = "pr_comment.csv"
CSV_POSTED_HEADER = ["REPO_ID_SUFFIX", "REPO_URL", "STATUS"]

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
    df[col_key] = df[col_key].str.lower()   # set the key column to lower case
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
    parser.add_argument("CONFIG", help="Python report builder configuration file.")
    parser.add_argument(
        "REPORT_FOLDER", nargs="?", help="Folder containing student report files."
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
    parser.add_argument("--ignore", nargs="+", help="if given, ignore these repos.")
    parser.add_argument(
        "--ghu",
        type=str,
        default="GHU",
        help="if given, only the teams specified will be parsed (Default: %(default)s).",
    )
    parser.add_argument(
        "--start",  
        "-s",
        type=int,
        default=1,
        help="repo no to start processing from (Default: %(default)s).",
    )
    parser.add_argument("--end", "-e", type=int, help="repo no to end processing.")
    parser.add_argument("--batch", "-b", type=int, help="batch to post (column BATCH, if any).")
    parser.add_argument(
        "--extension",
        "-ext",
        default="txt",
        help="Extension of report file (Default: %(default)s).",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        default=False,
        help="Do not push the automarking report; just feedback result %(default)s.",
    )
    parser.add_argument(
        "--no-feedback",
        action="store_true",
        default=False,
        help="Do not push the feedback summary; just the report %(default)s.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Do not push to repos, just report on console %(default)s.",
    )
    args = parser.parse_args()
    print(args)
    logger.info(f"Starting on {TIMEZONE}: {NOW_ISO}")

    # if there is no report folder, then no report posting!
    if args.REPORT_FOLDER is None:
        args.no_report = True

    if not os.path.isfile(args.CONFIG):
        logger.error(f"Feedback builder configuration file {args.CONFIG} not found or not a file.")
        exit(1)

    if not os.path.isfile(args.REPO_CSV):
        logger.error(f"Repo CSV file {args.REPO_CSV} not found.")
        exit(1)

    if not os.path.isfile(args.MARKING_CSV):
        logger.error(f"Marking CSV file {args.MARKING_CSV} not found.")
        exit(1)

    if args.REPORT_FOLDER and not Path(args.REPORT_FOLDER).is_dir():
        logger.error(
            f"Report folder {args.REPORT_FOLDER} not found or not a directory."
        )
        exit(1)

    if args.no_report and args.no_feedback:
        logger.error(
            f"Nothing to post as both --no-report and --no-feedback were set. Please check your options."
        )
        exit(1)

    if (args.start != 1 or args.end) is not None and (args.repos or args.ignore):
        logger.error(
            f"Cannot use --start/--end and --repos/--ignore at the same time. Please check your options."
        )
        exit(1)

    if (args.start < 1) or (args.end and args.start > args.end):
        logger.error(
            f"Start number has to be 1+ and less than --end."
        )
        exit(1)

    ###############################################
    # Load feedback report builder module and marking spreadsheet
    # https://medium.com/@Doug-Creates/dynamically-import-a-module-by-full-path-in-python-bbdf4815153e
    ###############################################
    spec = importlib.util.spec_from_file_location(
        "module_name", args.CONFIG
    )
    module_feedback = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module_feedback)
    # Add the module to sys.modules
    sys.modules["module_name"] = module_feedback

    # these MUST be defined in the report builder
    FEEDBACK_REPORT = getattr(module_feedback, "FEEDBACK_REPORT")
    result_feedback = getattr(module_feedback, "result_feedback")
    check_submission = getattr(module_feedback, "check_submission")

    #  feedback file may say which repos to process
    try:
        get_repos = getattr(module_feedback, "get_repos")
    except AttributeError:
        get_repos = lambda: None

    # load the marking dictionary from the CSV file
    marking_dict = load_marking_dict(args.MARKING_CSV, col_key=args.ghu)

    ###############################################
    # Filter repos as requested
    ###############################################
    # get the specific repos to process (if any)
    repos_process = args.repos or get_repos()
    # get all the repos available in the repo CSV database
    repos = util.get_repos_from_csv(
        args.REPO_CSV,
        repos_process,
        args.ignore,
    )

    # TODO: start and end clashes badly if ignore, repos, or get_repos are used
    # only allow --start and --end if no repos or ignore are given
    start_no = 1 
    end_no = len(repos)
    if repos_process is None:
        start_no = args.start if args.start is not None else 1
        end_no = args.end if args.end is not None else len(repos)
        logger.info(f"Getting repos {start_no} to {end_no}")
        repos = repos[args.start - 1 : end_no]

    if len(repos) == 0:
        logger.error(f'No relevant repos found in the mapping file "{args.REPO_CSV}". Stopping.')
        exit(0)

    logger.info(f"Number of relevant repos found: {len(repos)}")

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
    no_repos = len(repos)
    errors_csv = []
    posted_csv = []
    for k, r in enumerate(repos):
        if k % SLEEP_RATE == 0 and k > 0:
            logger.info(f"Sleep for {SLEEP_TIME} seconds...")
            time.sleep(SLEEP_TIME)

        repo_no = r["NO"]
        repo_id = r["REPO_ID_SUFFIX"].lower()
        repo_name = r["REPO_ID"]
        # repo_url = f"https://github.com/{repo_name}"
        repo_url = r["REPO_HTTP"]
        logger.info(
            f"Processing repo {k+start_no}/{end_no}: {repo_no}:{repo_id} ({repo_url})..."
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
                            f"\t Feedback PR found in number {pr.number}! Using this one: {repo_url}/pull/{pr.number}"
                        )
                        pr_feedback = repo.get_issue(number=pr.number)
                        break
                if pr_feedback is None:
                    logger.error("\t Feedback PR not found! Skipping...")
                    errors_csv.append([repo_id, repo_url, "Feedback PR not found"])
                    continue
            logger.debug(f"\t Feedback PR found: {pr_feedback}")

            # get the marking data for the student/repo
            if repo_id not in marking_dict:
                logger.error(
                    f"\t Repo {repo_id} not found in marking dictionary! Skipping..."
                )
                errors_csv.append([repo_id, repo_url, "missing_marking"])
                continue
            marking_repo = marking_dict[repo_id]

            # First, should we skip submission it for any reason?
            # (e.g., no certification/submission/marking, audit)
            message, skip, skip_reason = check_submission(repo_id, marking_repo, args.batch, logger)
            if message is not None:
                issue_feedback_comment(pr_feedback, message, args.dry_run)
                logger.info(f"\t Feedback warning/error posted to {pr_feedback.html_url}.")
                if not args.dry_run:
                    posted_csv.append([repo_id, repo_url, skip_reason])
            if skip:
                continue

            # Here there is a proper submission!
            # Issue the autograder report & feedback summary

            # First, create a new comment in PR with automarker report (if any)
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
                    errors_csv.append([repo_id, repo_url, "Report not found"])
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

                    message = f"# Feedback Report ✅\n\n ```{args.extension}\n{report_text}```"
                    if error_text is not None:
                        message += f"\n**NOTE**: {error_text}"
                    message += f"\n{FEEDBACK_REPORT}"
                    issue_feedback_comment(pr_feedback, message, args.dry_run)

            # Second, create COMMENT with the feedback summary
            if not args.no_feedback:
                feedback_text = result_feedback(marking_repo)
                if feedback_text is not None:
                    message = f"Dear @{repo_id}: find here the FEEDBACK & RESULTS for the project. \n\n {feedback_text}"
                    message = feedback_text
                    issue_feedback_comment(pr_feedback, message, args.dry_run)

            logger.info(f"\t Feedback comment/report posted to {pr_feedback.html_url}.")
            if not args.dry_run:
                posted_csv.append([repo_id, repo_url, "OK"])

        except GithubException as e:
            logger.error(f"\t Error in repo {repo_name}: {e}")
            errors_csv.append([repo_id, repo_url, e])
        except Exception as e:
            logger.error(
                f"\t Unknown error in repo {repo_name}: {e} \n {traceback.format_exc()}"
            )
            errors_csv.append([repo_id, repo_url, e])

    logger.info(f"Finished! Total repos: {no_repos} - Errors: {len(errors_csv)}.")

    add_csv(
        CSV_ERRORS,
        CSV_ERRORS_HEADER,
        errors_csv,
        append=True,
        timestamp=NOW_TXT,
    )  # write the errors to a CSV file
    add_csv(
        CSV_POSTED,
        CSV_POSTED_HEADER,
        posted_csv,
        append=True,
        timestamp=NOW_TXT,
    )  # write the errors to a CSV file

    logger.info(f"Repos with errors written to {CSV_ERRORS}.")
