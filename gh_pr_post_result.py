"""
Bulk-post marking results/feedback to the "Feedback" GitHub Issue/PR of many student repos.

Uses PyGithub (https://github.com/PyGithub/PyGithub) as API to GitHub:

    python3 -m pip install PyGithub

PyGithub documentation: https://pygithub.readthedocs.io/en/latest/introduction.html
Other doc on PyGithub: https://www.thepythoncode.com/article/using-github-api-in-python

For each repo, the script posts up to two comments on the repo's "Feedback" issue
(found as issue #1, or by searching pull requests titled "Feedback"):

1. the automarker report (read from a file), wrapped with any BEFORE/AFTER text
   defined by the report builder config
2. a feedback/result summary message, built by the report builder config from the
   student's row in the marking CSV

Use --no-report or --no-feedback to post only one of the two. Using --no-report
alone effectively turns this into a generic "post a message to the Feedback PR"
tool (e.g., to announce which commit was marked, or the submission date).

Usage:

    python gh_pr_post_result.py REPO_CSV MARKING_CSV CONFIG.py [REPORT_FOLDER] [options]

Positional arguments:

- REPO_CSV: CSV listing the repos to process, as produced by the repo-collection
  scripts in this toolset. Must have columns NO, REPO_ID_SUFFIX, REPO_ID, REPO_HTTP
  (see REPOS_HEADER_CSV in util.py).
- MARKING_CSV: CSV with one row per student/team with marking data (marks, feedback
  text, BATCH, etc.). Rows are keyed by the column named by --ghu (default "GHU"),
  matched case-insensitively against REPO_ID_SUFFIX. A "REPORT" column, if present,
  overrides the automarker report filename for that row; a "BATCH" column is used by
  --batch filtering.
- CONFIG: a Python file (the "report builder") that defines how feedback is built.
  It must define:
    * FEEDBACK_REPORT_BEFORE / FEEDBACK_REPORT_AFTER: text (or None) wrapped around
      the automarker report when posted
    * result_feedback(mapping) -> str | None: builds the feedback/result summary
      message from the student's marking-CSV row (a dict); return None to skip
    * check_submission(repo_id, mapping, batch, logger) -> (message, skip, skip_reason):
      decides whether/what to post before the report+feedback (e.g., to warn about a
      late or missing submission); `message` (or None) is posted first, and if `skip`
      is True the repo is skipped entirely
  and may optionally define:
    * get_repos() -> list[str] | None: restricts which repos to process (same effect
      as --repos)
  See feedback_p0.py / feedback_p2.py in this folder for examples.
- REPORT_FOLDER: [optional] folder with automarker report files, one per repo, named
  "<repo_id>.<extension>" (or "<repo_id>_ERROR.<extension>" to flag a non-error-free
  submission, which takes precedence if present). If omitted, no report is posted
  (equivalent to --no-report).

Key options:

- -t/--token: GitHub auth token, as a literal string or a path to a file containing it
- --repos STR...: only process these REPO_ID_SUFFIX values
- --ignore STR...: skip these REPO_ID_SUFFIX values
- --ghu STR: marking-CSV column used as the repo key (default "GHU")
- --start/-s, --end/-e: process only repos numbered in this range (mutually exclusive
  with --repos/--ignore/--batch)
- --batch/-b STR: only process repos whose marking-CSV "BATCH" column matches
- --extension/-ext STR: automarker report file extension (default "txt")
- --no-report / --no-feedback: skip the report comment / the feedback comment
- --dry-run: print messages to console instead of posting to GitHub

Example:

    $ python ../tools/git-teaching-tools.git/gh_pr_post_result.py repos.csv marking.csv feedback_p2.py reports -t ~/.ssh/keys/gh-token-ssardina.txt --repos ssardina

Output: appends to pr_comment.csv (successful posts) and pr_comment_errors.csv
(repos that failed or were skipped), each timestamped.
"""
__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2024-2026"
import os
import sys
import traceback
import time
from argparse import ArgumentParser
from pathlib import Path
from github import GithubException
import importlib.util

from github.Issue import Issue
from github.IssueComment import IssueComment

import util, utils_gh
from util import (
    NOW_ISO,
    TIMEZONE,
    NOW_TXT,
    add_csv,
)

SCRIPT_NAME = "pr_post_result"

from slogger.loguru_backend import Slogger

logger = Slogger(source=SCRIPT_NAME, timezone=TIMEZONE.key)


#####################################
# LOCAL GLOBAL VARIABLES FOR SCRIPT
#####################################
CSV_ERRORS = "pr_comment_errors.csv"
CSV_ERRORS_HEADER = ["REPO_ID_SUFFIX", "REPO_URL", "ERROR"]

CSV_POSTED = "pr_comment.csv"
CSV_POSTED_HEADER = ["REPO_ID_SUFFIX", "REPO_URL", "PR_URL", "STATUS"]

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
    df[col_key] = df[col_key].str.lower()  # set the key column to lower case
    df.set_index(col_key, inplace=True)
    df = df.round(2)
    comment_dict = df.to_dict(orient="index")
    for x in comment_dict:
        comment_dict[x][col_key] = x

    return comment_dict


def issue_feedback_comment(
    pr: Issue, message: str, dry_run=False
) -> IssueComment | None:
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
        "--token",
        # default=os.environ.get("GHTOKEN") or os.environ.get("GH_TOKEN"),
        help="File or string containing GitHub authorization token/password.",
    )
    parser.add_argument(
        "--repos",
        nargs="+",
        metavar="STR",
        help="if given, only the teams specified will be parsed.",
    )
    parser.add_argument(
        "--ignore", 
        nargs="+", 
        metavar="STR",
        help="if given, ignore these repos.")
    parser.add_argument(
        "--ghu",
        type=str,
        default="GHU",
        metavar="STR",
        help="Column name in marking spreadsheet identifying repositories, e.g., GHU or GH-TEAMS (Default: %(default)s).",
    )
    parser.add_argument(
        "--start",
        "-s",
        type=int,
        default=1,
        metavar="INT",
        help="repo no to start processing from (Default: %(default)s).",
    )
    parser.add_argument(
        "--end", "-e", type=int, metavar="INT", help="repo no to end processing."
    )
    parser.add_argument(
        "--batch", 
        "-b", 
        type=str,
        help="batch to post (column BATCH, if any).")
    parser.add_argument(
        "--extension",
        "-ext",
        metavar="STR",
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
    else:
        args.REPORT_FOLDER = Path(args.REPORT_FOLDER)

    if not os.path.isfile(args.CONFIG):
        logger.error(
            f"Feedback builder configuration file {args.CONFIG} not found or not a file."
        )
        exit(1)

    if not os.path.isfile(args.REPO_CSV):
        logger.error(f"Repo CSV file {args.REPO_CSV} not found.")
        exit(1)

    if not os.path.isfile(args.MARKING_CSV):
        logger.error(f"Marking CSV file {args.MARKING_CSV} not found.")
        exit(1)

    if args.REPORT_FOLDER and not args.REPORT_FOLDER.is_dir():
        logger.error(
            f"Report folder {args.REPORT_FOLDER} not found or not a directory."
        )
        exit(1)

    if args.no_report and args.no_feedback:
        logger.error(
            f"Nothing to post as both --no-report and --no-feedback were set. Please check your options."
        )
        exit(1)

    if (args.start != 1 or args.end) is not None and (args.repos or args.ignore or args.batch):
        logger.error(
            f"Cannot use --start/--end and --repos/--ignore/--batch at the same time. Please check your options."
        )
        exit(1)

    if (args.start < 1) or (args.end and args.start > args.end):
        logger.error(f"Start number has to be 1+ and less than --end.")
        exit(1)

    ###############################################
    # Load feedback report builder module and marking spreadsheet
    # https://medium.com/@Doug-Creates/dynamically-import-a-module-by-full-path-in-python-bbdf4815153e
    ###############################################
    spec = importlib.util.spec_from_file_location("module_name", args.CONFIG)
    module_feedback = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module_feedback)
    # Add the module to sys.modules
    sys.modules["module_name"] = module_feedback

    # these MUST be defined in the report builder
    FEEDBACK_REPORT_BEFORE = getattr(module_feedback, "FEEDBACK_REPORT_BEFORE")
    FEEDBACK_REPORT_AFTER = getattr(module_feedback, "FEEDBACK_REPORT_AFTER")
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
    # Filter repos as requested:
    #
    #   - if --repos is given or get_repos(), only those repos will be processed
    #   - if --batch is given, only the repos with that batch in the marking
    #   - if --start and/or --end is given, only the repos in that range will be processed
    ###############################################
    # get the specific repos that are to be processed (if any)
    repos_process = args.repos or get_repos()

    # get all the repos available in the repo CSV database
    repos = util.get_repos_from_csv(
        args.REPO_CSV,
        repos_process,
        args.ignore,
    )

    # if --batch used, filter repos
    repos = [r for r in repos if r["REPO_ID_SUFFIX"].lower() in marking_dict]
    # make BATCH column a string (in case it is a number) to avoid problems with comparison
    for k in marking_dict:
        if type(marking_dict[k]["BATCH"]) == float:
            marking_dict[k]["BATCH"] = str(int(marking_dict[k]["BATCH"]))
    if args.batch is not None:
        repos = [
            x
            for x in repos
            if marking_dict[x["REPO_ID_SUFFIX"].lower()]["BATCH"] == args.batch
        ]

    start_no = 1
    end_no = len(repos)

    # only allow --start and --end if no other filtering used
    if repos_process is None and args.batch is None and not args.ignore:
        start_no = args.start if args.start is not None else 1
        end_no = args.end if args.end is not None else len(repos)
        logger.info(f"Getting repos {start_no} to {end_no}")
        repos = repos[args.start - 1 : end_no]

    if len(repos) == 0:
        logger.error(
            f'No relevant repos found in the mapping file "{args.REPO_CSV}". Stopping.'
        )
        exit(0)

    logger.info(f"Number of relevant repos found: {len(repos)}")

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
            message, skip, skip_reason = check_submission(
                repo_id, marking_repo, args.batch, logger
            )
            if message is not None:
                issue_feedback_comment(pr_feedback, message, args.dry_run)
                logger.info(
                    f"\t Feedback warning/error posted to {pr_feedback.html_url}."
                )
                if not args.dry_run:
                    posted_csv.append(
                        [repo_id, repo_url, pr_feedback.html_url, skip_reason]
                    )
            if skip:
                continue

            # Here there is a proper submission!
            # Issue the autograder report & feedback summary

            # First, create a new comment in PR with automarker report (if any)
            if not args.no_report:
                file_report = args.REPORT_FOLDER / f"{repo_id}.{args.extension}"
                file_report_error = (
                    args.REPORT_FOLDER / f"{repo_id}_ERROR.{args.extension}"
                )
                if "REPORT" in marking_repo:
                    file_report = args.REPORT_FOLDER / marking_repo["REPORT"]

                # if there is an error report, then use that one
                error_text = None
                if file_report_error.exists():
                    file_report = file_report_error
                    error_text = (
                        "Your solution seems non-error free as requested in spec... 🥴"
                    )
                if not file_report.exists():
                    logger.error(
                        f"\t Error in repo {repo_name}: report {file_report} (or _ERROR) not found."
                    )
                    errors_csv.append([repo_id, repo_url, "Report not found"])
                    continue
                if file_report.stat().st_size > 50000:
                    logger.warning(f"\t Too large automarker report to publish")
                    issue_feedback_comment(
                        pr_feedback,
                        f"Too large automarker report to publish... 🥴",
                        args.dry_run,
                    )
                else:
                    with open(file_report, "r") as report:
                        report_text = report.read()

                    message = f"# Feedback Report ✅\n\n"
                    if FEEDBACK_REPORT_BEFORE is not None:
                        message += FEEDBACK_REPORT_BEFORE
                    message += f"\n\n ```{args.extension}\n{report_text}```"
                    if error_text is not None:
                        message += f"\n**NOTE**: {error_text}"
                    if FEEDBACK_REPORT_AFTER is not None:
                        message += f"\n\n{FEEDBACK_REPORT_AFTER}"
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
                posted_csv.append([repo_id, repo_url, pr_feedback.html_url, "OK"])

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
