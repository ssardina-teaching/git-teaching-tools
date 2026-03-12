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
import util

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

START_CSV = f"workflows-start-{NOW_TXT}.csv"
JOBS_CSV = f"workflows-jobs-{NOW_TXT}.csv"
JOBS_HEADER_CSV = ["REPO_ID_SUFFIX", "REPO_ID", "REPO_URL", "RESULT", "HTML_URL"]

SLEEP_RATE = 10  # number of repos to process before sleeping
SLEEP_TIME = 5  # sleep time in seconds between API calls

def delete_workflow(
    repos: list,
    wrk_name: str,
    until_dt: datetime,
    run_name: str = None,
    dry_run: bool = False,
):
    """Delete latest workflow runs for repos until some date in the past (excluded)

    API for Workflows: https://pygithub.readthedocs.io/en/latest/github_objects/Workflow.html

    Args:
        repos (list): list of repos to process
        wrk_name (str): name of the workflow to run
        until_dt (datetime): all workflows after this date
        run_name (str, optional): name of the run.
    """
    no_repos = len(repos)
    output_csv = []
    no_errors = 0
    no_deleted = 0
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
        wrkflow: Workflow = None
        for w in repo.get_workflows():
            if wrk_name in w.name:
                wrkflow = w
                logger.info(f"\t Found workflow ({w})")
                break
        if wrkflow is None:
            logger.error(f"\t Workflow *{wrk_name}* not in {repo_name}.")
            no_errors += 1
            continue

        # we go over all worfklow RUNS of the workflow and delete if after until_dt
        for wr in wrkflow.get_runs():
            if run_name is not None and run_name not in wr.name:
                continue
            if wr.created_at > until_dt.astimezone(UTC):
                logger.info(
                    f"\t Workflow #{wr.run_number} run {wr.name} - {wr.created_at.astimezone(TIMEZONE)} - {wr.html_url} - deleting it..."
                )
                if not dry_run:
                    no_deleted += 1
                    try:
                        wr.delete()
                    except GithubException as e:
                        logger.error(f"\t Error deleting workflow run: {e}")
                        no_errors += 1
            else:
                # we have processed all workflow runs after until_dt
                break
    logger.info(f"Finished! No of repos processed: {no_repos} - Errors: {no_errors}")


def start_workflow(
    repos: list,
    wrk_name: str,
    commit: str,
    until_dt: datetime = None,
    run_name: str = None,
    dry_run: bool = False,
):
    """Dispatch a workflow to repos in list_repos

    API for Workflows: https://pygithub.readthedocs.io/en/latest/github_objects/Workflow.html

    Args:
        repos (list): list of repos to process
        wrk_name (str): name of the workflow to run
        commit (str): commit or branch to run the workflow on
        until_dt (datetime): last commit before this date
        run_name (str, optional): name of the run.
    """
    no_repos = len(repos)
    output_csv = []
    no_errors = 0
    for k, r in enumerate(repos, start=1):
        if k % SLEEP_RATE == 0 and k > 0:
            logger.info(f"Sleep for {SLEEP_TIME} seconds...")
            time.sleep(SLEEP_TIME)

        # get the current repo data
        repo_no = r["NO"]
        repo_id = r["REPO_ID_SUFFIX"]
        repo_name = r["REPO_ID"]
        repo_url = r["REPO_HTTP"]
        logger.info(
            f"Processing repo {k}/{no_repos}: {repo_no}:{repo_id} ({repo_url})..."
        )

        try:
            repo = g.get_repo(repo_name)

            # override commit if --until is given: get latest commit before until_dt
            if until_dt is not None:
                commits = repo.get_commits(until=until_dt.astimezone(UTC))
                if commits.totalCount == 0:
                    logger.info(f"\t No commits found before {until_dt.isoformat()}.")
                    continue
                commit = commits[0]  # last commit before until_dt
            else:
                # get the actual commit object (because commit may be just "main")
                commit = repo.get_commit(commit)

            commit_sha = commit.sha
            commit_sha_sort = commit_sha[:7]
            commit_date = commit.commit.author.date.astimezone(until_dt.tzinfo if until_dt else TIMEZONE).isoformat()
            logger.debug(
                f"\t Commit SHA to run workflow: {commit_sha_sort} - {commit_date}"
            )

            # check the commit has not been marked already
            if not args.remark:
                commit_statuses = commit.get_statuses()
                if commit_statuses is not None and commit_statuses.totalCount > 0:
                    logger.info(
                        f"\t Already marked with state: {commit_statuses[0].state}"
                    )
                    output_csv.append(
                        [repo_id, repo_name, repo_url, "already_marked", "", ""]
                    )
                    continue

            # get all workshops and find the one we are looking for (contains args.name)
            workflows = repo.get_workflows()
            workflow_selected = None
            for w in workflows:
                if  wrk_name in w.name:
                    logger.info(
                        f"\t Found workflow ({w}) - Dispatch it on commit {commit_sha_sort} - {commit_date}"
                    )
                    workflow_selected = w
                    break

            if workflow_selected is None:
                logger.info(
                    f"\t Workflow *{wrk_name}* not in {repo_name} - {repo_url}."
                )
                no_errors += 1
                output_csv.append([repo_id, repo_name, repo_url, "missing_workflow", "", ""])
                continue

            # we found the workflow, now run it on commit sha   !
            result = None
            if workflow_selected is not None:
                # https://pygithub.readthedocs.io/en/latest/github_objects/Workflow.html
                # This relies on the workshop handling BranchRef input!!
                inputs = {}
                if commit_sha is not None:
                    inputs["branch_ref"] = commit_sha
                if run_name is not None:
                    inputs["run_name"] = run_name

                # RUN the workflow on head of main; but the inputs have the sha that needs to be marked ;-) cool eh?
                result = True
                if not dry_run:
                    result = workflow_selected.create_dispatch(ref="main", inputs=inputs)
                if not result:
                    logger.error(
                        f"\t Workflow *{workflow_selected.name}* failed to start."
                    )
                    no_errors += 1
            else:
                no_errors += 1
            output_csv.append(
                [repo_id, repo_name, repo_url, result, commit_sha_sort, commit_date]
            )
        except GithubException as e:
            logger.error(f"\t Error in repo {repo_name}: {e}")
            output_csv.append([repo_id, repo_name, repo_url, "exception", "", ""])
            no_errors += 1

    logger.info(f"Finished! No of repos processed: {no_repos} - Errors: {no_errors}")

    if not dry_run:
        output_csv.sort()
        with open(START_CSV, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["REPO_ID_SUFFIX", "REPO_ID", "REPO_URL", "RESULT", "COMMIT_SHA", "COMMIT_DATE"])
            writer.writerows([row for row in output_csv])

    # for repo_id in output_csv:
    #     print(repo_id)

    logger.info(f"Workflow results data written to {START_CSV}.")


def get_jobs(
    repos: list,
    wrk_name: str,
    run_name: str = None,
):
    """Collect the HTML URL links for jobs run

        API for Workflows: https://pygithub.readthedocs.io/en/latest/github_objects/Workflow.html

    >>> repo = g.get_repo("RMIT-COSC2780-2973-IDM25/workshop-5-ghen")
    >>> wrs = repo.get_workflow_runs()
    >>> wrs[0].jobs()[0].__dict__.keys()
    dict_keys(['_requester', '_check_run_url', '_completed_at', '_conclusion', '_created_at', '_head_branch', '_head_sha', '_html_url', '_id', '_labels', '_name', '_node_id', '_run_attempt', '_run_id', '_run_url', '_runner_group_id', '_runner_group_name', '_runner_id', '_runner_name', '_started_at', '_status', '_steps', '_url', '_workflow_name', '_headers', '_rawData', '_CompletableGithubObject__completed'])
    >>> wrs[0].jobs()[0].html_url
    'https://github.com/RMIT-COSC2780-2973-IDM25/workshop-5-ghen/actions/runs/14393599639/job/40365263779'

    Args:
        repos (list): list of repos to process
        wrk_name (str): name of the workflow to run
        run_name (str, optional): name of the run.
    """
    no_repos = len(repos)
    output_csv = []
    no_errors = 0
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

        try:
            repo = g.get_repo(repo_name)

            # first we get the workflow we are after
            wrkflow : Workflow = None
            for w in repo.get_workflows():
                if wrk_name in w.name:
                    wrkflow = w
                    logger.info(f"\t Found workflow ({w})")
                    break

            if wrkflow is None:
                logger.info(f"\t Workflow *{wrk_name}* not in {repo_name}.")
                no_errors += 1
                output_csv.append(
                    [repo_id, repo_name, repo_url, "missing_workflow", ""]
                )
                continue

            # second, we get the worfklow RUN that we want
            wrkflow_runs = wrkflow.get_runs()
            wrkflow_run = None
            if run_name is not None:
                wrkflow_run = next(
                    (x for x in wrkflow_runs if run_name in x.name),
                    None,
                )
            else:
                wrkflow_run = wrkflow_runs[0] if wrkflow_runs.totalCount > 0 else None
            if wrkflow_run is None:
                logger.info(f"\t No workflow runs found for workflow {wrkflow.name}.")
                no_errors += 1
                output_csv.append(
                    [repo_id, repo_name, repo_url, "no_workflow_runs", ""]
                )
                continue

            # third we get its FIRST job (we know here there is one at least!)
            wrkflow_job_name = wrkflow_run.jobs()[0].name
            wrkflow_job_html = wrkflow_run.jobs()[0].html_url
            wrkflow_job_date = wrkflow_run.run_started_at.astimezone(TIMEZONE)

            logger.info(
                f"\t Found workflow run log: {wrkflow_job_name} - {wrkflow_job_date} - {wrkflow_job_html}"
            )
            output_csv.append(
                [repo_id, repo_name, repo_url, wrkflow_job_name, wrkflow_job_html]
            )
        except GithubException as e:
            logger.error(f"\t Error in repo {repo_name}: {e}")
            output_csv.append([repo_id, repo_name, repo_url, "exception", ""])
            no_errors += 1

    logger.info(f"Finished! No of repos processed: {no_repos} - Errors: {no_errors}")

    output_csv.sort()
    with open(JOBS_CSV, "w", newline="") as file:
        writer = csv.writer(file, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(JOBS_HEADER_CSV)
        writer.writerows([row for row in output_csv])

    logger.info(f"Results data written to CSV file: {JOBS_CSV}.")


if __name__ == "__main__":
    parser = ArgumentParser(description="Handle automarking workflows")
    parser.add_argument(
        "ACTION",
        choices=["start", "delete", "jobs", "status"],
        help="Action to do on workflows.",
    )
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
    parser.add_argument("--name", help="title of workflow to start.")
    parser.add_argument("--run-name", help="name of the run (if not default one).")
    parser.add_argument(
        "--commit",
        default="main",
        help="commit or branch to execute it on %(default)s.",
    )
    parser.add_argument(
        "--until",
        help="Last commit before this date. Datetime in ISO format, e.g., 2025-04-09T15:30. Overrides --commit.",
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
        "--remark",
        default=False,
        action="store_true",
        help="Remark even if commit was already marked (Default: %(default)s).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Do not push to repos, just report on console %(default)s.",
    )
    args = parser.parse_args()
    logger.info(f"Starting script on {TIMEZONE}: {NOW_ISO}")

    if args.name is None:
        logger.error("You must provide a name for the workflow to run.")
        exit(1)

    ###############################################
    # Filter repos as desired
    ###############################################
    # Get the list of TEAM + GIT REPO links from csv file
    list_repos = util.get_repos_from_csv(args.REPO_CSV, args.repos)
    if args.repos is None:
        end_no = args.end if args.end is not None else len(list_repos)
        list_repos = list_repos[args.start - 1 : end_no]

    if len(list_repos) == 0:
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
    until_dt = None
    if args.until is not None:
        until_dt = datetime.fromisoformat(args.until)
        if until_dt.tzinfo is None:
            until_dt = until_dt.replace(tzinfo=TIMEZONE)
        logger.info(
            f"Will run workflow on last commit before date: {until_dt.isoformat()} - UTC: {until_dt.astimezone(UTC).isoformat()}"
        )

    if args.ACTION == "start":
        start_workflow(
            repos=list_repos,
            wrk_name=args.name,
            commit=args.commit,
            until_dt=until_dt,
            run_name=args.run_name,
            dry_run=args.dry_run
        )
    elif args.ACTION == "delete":
        delete_workflow(
            repos=list_repos,
            wrk_name=args.name,
            until_dt=until_dt,
            run_name=args.run_name,
            dry_run=args.dry_run
        )
    elif args.ACTION == "jobs":
        get_jobs(
            repos=list_repos,
            wrk_name=args.name,
            run_name=args.run_name,
        )
