"""
Check which repos are missing PR #1 for Feedback from GitHub Classroom; create PR if needed

Uses PyGithub (https://github.com/PyGithub/PyGithub) as API to GitHub:

    python3 -m pip install PyGithub

PyGithub documentation: https://pygithub.readthedocs.io/en/latest/introduction.html
Other doc on PyGithub: https://www.thepythoncode.com/article/using-github-api-in-python
"""
__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2024-2025"

import csv
from argparse import ArgumentParser

# https://pygithub.readthedocs.io/en/latest/introduction.html
from github import Github, GithubException

import util, utils_gh
from util import (
    TIMEZONE,
    NOW_ISO,
    NOW_TXT,
    LOGGING_DATE,
    LOGGING_FMT,
    add_csv,
)
SCRIPT_NAME = "gh_pr_feedback_create"


import logging
import coloredlogs
LOGGING_LEVEL = logging.INFO
# LOGGING_LEVEL = logging.DEBUG
# logger.basicConfig(format=LOGGING_FMT, level=LOGGING_LEVEL, datefmt=LOGGING_DATE)
logger = logging.getLogger(__name__)
coloredlogs.install(level=LOGGING_LEVEL, fmt=LOGGING_FMT, datefmt=LOGGING_DATE)

#####################################
# LOCAL GLOBAL VARIABLES FOR SCRIPT
#####################################

# Application global variables
CSV_OUTPUT = "pr_create.csv"
CSV_HEADER = ["REPO_ID_SUFFIX", "REPO_URL", "RESULT", "DETAILS"]
MESSAGE_PR = """
:wave:! GitHub Classroom created this pull request as a place for your teacher to leave feedback on your work. It will update automatically. **Don’t close or merge this pull request**, unless you’re instructed to do so by your teacher.
 In this pull request, your teacher can leave comments and feedback on your code. Click the **Subscribe** button to be notified if that happens.
 Click the **Files changed** or **Commits** tab to see all of the changes pushed to `main` since the assignment started. Your teacher can see this too.
<details>
<summary>
<strong>Notes for teachers</strong>
</summary>

 Use this PR to leave feedback. Here are some tips:
 - Click the **Files changed** tab to see all of the changes pushed to `main` since the assignment started. To leave comments on specific lines of code, put your cursor over a line of code and click the blue **+** (plus sign). To learn more about comments, read “[Commenting on a pull request](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/commenting-on-a-pull-request)”.
- Click the **Commits** tab to see the commits pushed to `main`. Click a commit to see specific changes.
- If you turned on autograding, then click the **Checks** tab to see the results.
- This page is an overview. It shows commits, line comments, and general comments. You can leave a general comment below.
 For more information about this pull request, read “[Leaving assignment feedback in GitHub](https://docs.github.com/education/manage-coursework-with-github-classroom/leave-feedback-with-pull-requests)”.
</details>


Subscribed: @{GH_USERNAME}
"""

if __name__ == "__main__":
    parser = ArgumentParser(description="Merge PRs in multiple repos")
    parser.add_argument("REPO_CSV", help="List of repositories to get data from.")
    parser.add_argument(
        "BASE_SHA", nargs="?", help="Base SHA to create feedback branch from (Defaults to first commit in main)."
    )
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
        "--dry-run",
        action="store_true",
        default=False,
        help="Do not push to repos, just report on console (Default: %(default)s.)",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        default=False,
        help="Dump results into CSV files (Default: %(default)s.)",
    )
    args = parser.parse_args()
    logger.info(f"Starting on {TIMEZONE}: {NOW_ISO} - {args}")

    if args.BASE_SHA is None:
        logger.warning("No base SHA given, will use first commit in main.")

    ###############################################
    # Filter repos as desired
    ###############################################
    list_repos = util.get_repos_from_csv(args.REPO_CSV, args.repos)
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
        g = utils_gh.open_gitHub(token_file=args.token_file)
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
    output_csv = []
    for k, r in enumerate(list_repos, start=1):
        repo_no = r["NO"]
        repo_id = r["REPO_ID_SUFFIX"]
        repo_name = r["REPO_ID"]
        repo_url = r["REPO_HTTP"]
        logger.info(
            f"Processing repo {k}/{no_repos}: {repo_no}:{repo_id} ({repo_url})..."
        )

        repo = g.get_repo(repo_name)

        # first check that no force-pushed has over-written main branch
        commits = repo.get_commits("main")
        no_commits = commits.totalCount
        first_commit_main = commits[commits.totalCount - 1]

        # if no sha given, use the first commit in main
        base_sha = args.BASE_SHA if args.BASE_SHA else first_commit_main.sha

        if first_commit_main.sha != base_sha:
            logger.error(f"\t First commit is different from expected, forced pushed?")
            output_csv.append([repo_id, repo_url, "error_forced", first_commit_main.sha])
            continue

        # OK first commit in main exists, let's check if the PR exists and create it if not
        try:
            pr_feedback = repo.get_pull(number=1)  

            if pr_feedback.title != "Feedback":
                logger.error(f"\t PR with different title {pr_feedback.title}")
                output_csv.append([repo_id, repo_url, "error_title", pr_feedback.title])
                continue

            if pr_feedback.merged:
                logger.info(f"\t PR Feedback merged!!! {pr_feedback}")
                output_csv.append([repo_id, repo_url, "error_merged", ""])
                continue
        except GithubException as e:
            # if we get here, there is no FEEDBACK PR #1!
            # now we are talking...
            if e.status == 404:
                logger.info(
                    f"\t No Feedback PR #1 found in repo {repo_name}. We will create it..."
                )
            else:
                logger.error(f"\t Unknown exception getting PR Feedback: {e}")
                output_csv.append([repo_id, repo_url, "excepton_get_pr", e])
                continue

            # get the slug to @mentioning in PR text
            slug = repo_id
            repo_teams = repo.get_teams()
            if repo_teams.totalCount > 0:
                # get the first team slug
                slug = repo_teams[0].slug
                logger.info(f"\t Using slug {slug} for @mentioning.")

            # we know PR is missing, so we will create it
            if args.dry_run:
                pr_message = f"\t Dry run!!!: Would create feedback branch at SHA {base_sha} and Feedback PR with body: \n \t {MESSAGE_PR.format(GH_USERNAME=slug)}"
                logger.info(
                    f"\t Dry run!!!: Would create feedback branch at SHA {base_sha[:7]} and Feedback PR with following message:\n {pr_message}"
                )
                output_csv.append([repo_id, repo_url, "dry-run", {base_sha[:7]}])
                continue

            # FIRST, create a feedback branch from the base SHA
            try:
                repo.create_git_ref("refs/heads/feedback", base_sha)
                logger.info(
                    f"\t Created feedback branch at SHA {base_sha[:7]}."
                )
            except GithubException as e:
                if e.data["message"] == "Reference already exists":
                    logger.info(f"\t Branch 'feedback' already exists.")
                else:
                    logger.error(f"\t Error creating branch 'feedback': {e}")
                    output_csv.append([repo_id, repo_url, "exception_create_branch", e])
                    continue

            # SECOND, create a PR for feedback branch
            # there must be at least one commit in the main to be able to PR into a feedback PR - create a dummy commit otherwise
            if no_commits == 1:
                logger.warning(f"\t No commits in main branch yet, need to create a dummy one to create PR.")
                keep_file = ".github/keep"
                keep_content = " "
                # Check if the file already exists
                try:
                    existing_file = repo.get_contents(keep_file)
                    # File exists – update it
                    repo.update_file(
                        path=keep_file,
                        message="Setting up GitHub Classroom Feedback",
                        content=keep_content,
                        sha=existing_file.sha,
                    )
                except Exception:
                    # File does not exist – create it
                    repo.create_file(
                        path=keep_file,
                        message="Setting up GitHub Classroom Feedback",
                        content=keep_content,
                    )

                logger.info(f"\t Dummy file {keep_file} was updated/created.")
            # time to create the PR
            try:
                repo.create_pull(
                    title="Feedback",
                    body=MESSAGE_PR.format(GH_USERNAME=repo_id),
                    head="main",
                    base="feedback",    # {R from main to feedback
                )
            except GithubException as e:
                logger.error(f"\t Exception when creating PR in repo {repo_name}: {e}")
                if e.data["message"] == "Validation Failed":
                    # This should not happen anymore as we create a dummy commit in main to be able to PR into feedback
                    logger.error(f"\t Perhaps no commits exist in repo.")
                    output_csv.append(
                        [repo_id, repo_url, "exception_validation", e]
                    )
                else:
                    output_csv.append([repo_id, repo_url, "exception_create", e])
                    break
                continue

            # all good! PR was created SUCCESSFULLY!
            output_csv.append([repo_id, repo_url, "created", ""])

    # print summary stats
    no_merged = len([x for x in output_csv if x[2] == "error_merged"])
    no_errors = len([x for x in output_csv if not x[2] in ["created", "dry-run"]])
    logger.info(
        f"Finished! Total repos: {no_repos} - Merged PR: {no_merged} - Missing PR: {len(output_csv)} - Errors: {no_errors}."
    )

    output_csv = sorted(output_csv, key=lambda x: x[2])
    add_csv(
        CSV_OUTPUT,
        CSV_HEADER,
        output_csv,
        append=True,
        timestamp=NOW_TXT,
        quoting=csv.QUOTE_NONNUMERIC,
    )

    logger.info(f"Output written to CSF file: {CSV_OUTPUT}.")

    # just for manual debug.. ouch!
    # for r in output_csv:
    #     print(r)
