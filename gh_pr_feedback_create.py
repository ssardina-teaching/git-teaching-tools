"""
gh_pr_feedback_create.py

Ensure every student repo has an open GitHub Classroom "Feedback" pull request,
creating it (and its `feedback` base branch) when missing, so teachers have a single
persistent place to leave feedback and see autograding results.

BACKGROUND
    GitHub Classroom normally opens a "Feedback" PR (head=`main`, base=`feedback`) as
    soon as a student's repo has its first commit. That PR stays open for the whole
    unit and is where teachers comment on submitted work. Sometimes Classroom fails to
    create it (e.g. repo created before a commit existed, Classroom hiccup, manual repo
    setup) or a teacher/student closes or merges it by mistake. This script audits a
    batch of repos and repairs any that are missing a valid Feedback PR.

WHAT IT DOES, per repo in the input CSV:
    1. Fetches commits on `main` and takes the FIRST commit's SHA as the expected base.
       If it does not match BASE_SHA (when given), the repo is flagged as possibly
       force-pushed and skipped (result "error_forced") — this is a safety check so we
       never anchor a feedback branch to unexpected history.
    2. Searches ALL pull requests (any state, oldest first) for one titled exactly
       "Feedback" — it is NOT assumed to be PR #1, since an earlier issue or PR in the
       same repo shifts the numbering (e.g. issue #1 exists, so the Feedback PR is #2):
         - If a matching PR is found and has been merged                -> "error_merged", skipped.
         - If a matching PR is found and is not merged (open or closed) -> nothing to do (no CSV row).
         - If no matching PR is found                                    -> proceed to create it.
         - Any API error while listing PRs                                -> "exception_get_pr", skipped.
    3. To create the missing PR:
         a. Resolves an @mention slug for the PR body: the repo's first GitHub Team slug
            if the repo belongs to a team, else the REPO_ID_SUFFIX (assumed to be the
            student's username).
         b. Creates branch `feedback` pointing at the base SHA (ignored if it already
            exists).
         c. If `main` has only the single starter commit, GitHub Classroom PRs require at
            least one commit of difference to open a PR into `feedback`, so a dummy file
            `.github/keep` is created/updated on `main` first.
         d. Opens the PR: title "Feedback", head `main` -> base `feedback`, body filled in
            from MESSAGE_PR (welcome message, autograding link, notes-for-teachers block).

USAGE
    python3 gh_pr_feedback_create.py REPO_CSV [BASE_SHA] [--repos ID ...] [-t TOKEN]
                                      [--dry-run] [--csv]

    REPO_CSV   CSV with (at least) columns REPO_ID_SUFFIX, REPO_ID, REPO_HTTP — see
               util.get_repos_from_csv() / util.REPOS_HEADER_CSV for the expected shape
               (as produced by the roster-building scripts in this repo).
    BASE_SHA   Expected SHA of the first commit on `main` (the Classroom starter
               commit). If omitted, whatever the first commit on `main` happens to be is
               trusted as the base — the force-push safety check is effectively disabled
               per repo in that case.
    --repos    Restrict processing to these REPO_ID_SUFFIX values (case-insensitive).
    -t/--token GitHub token: a literal token string, a path to a file containing one, or
               (if omitted) the GHTOKEN/GH_TOKEN environment variable. Needs repo scope
               (create branches/files/PRs) on the target org.
    --dry-run  Report what would happen without creating branches, files, or PRs.
    --csv      Also present for interface consistency with sibling scripts; note that a
               CSV report (CSV_OUTPUT, default "pr_create.csv") is currently always
               appended regardless of this flag (see suggested improvements below).

OUTPUT
    - Console/log output per repo via Slogger.
    - CSV_OUTPUT (default "pr_create.csv"), appended with one row per repo that needed
      attention (repos that already had a healthy Feedback PR are NOT logged), columns:
      REPO_ID_SUFFIX, REPO_URL, RESULT, DETAILS, TIMESTAMP. RESULT is one of: "created",
      "dry-run", "error_forced", "error_merged", "exception_get_pr",
      "exception_create_branch", "exception_create_dummy_file", "exception_validation",
      "exception_create", "exception_unexpected" (any error not caught above, e.g. rate
      limits exhausted after PyGithub's built-in retries).
    - A one-line summary log: total repos, merged-PR count, missing-PR count, error count.

REQUIREMENTS
    PyGithub (https://github.com/PyGithub/PyGithub):

        python3 -m pip install PyGithub

    PyGithub docs: https://pygithub.readthedocs.io/en/latest/introduction.html
    Other doc on PyGithub: https://www.thepythoncode.com/article/using-github-api-in-python
"""
__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2024-2026"

import csv
from argparse import ArgumentParser
import traceback

# https://pygithub.readthedocs.io/en/latest/introduction.html
from github import Github, GithubException

import util, utils_gh
from util import (
    TIMEZONE,
    NOW_ISO,
    NOW_TXT,
    add_csv,
)
SCRIPT_NAME = "gh_pr_feedback_create"

# setup my own logger for this script, using the slogger/loguru backend
from slogger.loguru_backend import logger, setup_logger

setup_logger(source=SCRIPT_NAME, timezone=TIMEZONE.key)


PR_TITLE = "Feedback"
CALLS_PER_REPO_ESTIMATE = 5  # rough estimate of API calls per repo for this script

#####################################
# LOCAL GLOBAL VARIABLES FOR SCRIPT
#####################################

# Application global variables
CSV_OUTPUT = "pr_create.csv"
CSV_HEADER = ["REPO_ID_SUFFIX", "REPO_URL", "RESULT", "DETAILS"]
MESSAGE_PR = """
:wave:! Classroom 50 opened this pull request as a place for your teacher to leave feedback on your work. It stays up to date automatically as you push. **Don't close or merge this pull request** unless your teacher tells you to.

Each commit is automatically graded — the latest autograding result is [here](https://github.com/RMIT-COSC1127-3117-AI/ai26-p0-warmup-{GH_USERNAME}/releases/latest).

Your teacher can leave comments and feedback on your code here. Click the **Subscribe** button to be notified when that happens.

Open the **Files changed** or **Commits** tab to see everything you've pushed to `main` since you accepted the assignment — your teacher sees the same view.

<details>
<summary><strong>Notes for teachers</strong></summary>

Use this PR to leave feedback:

- **Files changed** shows the full diff on `main` since the student accepted. Hover a line and click the blue **+** to leave a line comment.
- **Commits** lists each pushed commit; open one to see its changes.
- Autograde results appear as the `classroom50/autograde` commit status / check on each submission.
- The [latest autograding result](https://github.com/RMIT-COSC1127-3117-AI/ai26-p0-warmup-{GH_USERNAME}/releases/latest) has the per-test detail behind that status.
- This page is an overview — commits, line comments, and a general comment box below.

The base branch (`feedback`) is frozen at the starter so the diff always reflects the full body of work. The PR is kept up to date automatically; merging it is the teacher-side "grading done" signal.
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
        "--title", 
        default=PR_TITLE, 
        help="Title of the PR to create (Default: %(default)s)."
    )
    parser.add_argument(
        "--repos", nargs="+", help="if given, only the teams specified will be parsed."
    )
    parser.add_argument(
        "-t",
        "--token",
        # default=os.environ.get("GHTOKEN") or os.environ.get("GH_TOKEN"),
        help="File or string containing GitHub authorization token/password.",
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
    try:
        g = utils_gh.open_gitHub(token=args.token)
    except Exception as e:
        logger.error(
            "Something wrong happened during GitHub authentication. Check credentials."
        )
        traceback.print_exc()
        exit(1)

    # PyGithub retries/backs off on rate limits automatically (see github.GithubRetry),
    # but warn upfront if we are already low on quota for this batch.
    core_rate = g.get_rate_limit().rate
    logger.info(
        f"GitHub API rate limit: {core_rate.remaining}/{core_rate.limit} remaining, "
        f"resets at {core_rate.reset.astimezone(TIMEZONE).isoformat()}."
    )
    no_repos_estimate = len(list_repos) * CALLS_PER_REPO_ESTIMATE  # rough: ~5 API calls per repo
    if core_rate.remaining < no_repos_estimate:
        logger.warning(
            f"Only {core_rate.remaining} API calls left but processing {len(list_repos)} "
            f"repos may need ~{no_repos_estimate}. This run may stall/fail on rate limits.",
            indent=2,
        )

    ###############################################
    # Process each repo in list_repos
    ###############################################
    no_repos = len(list_repos)
    output_csv = []
    for k, r in enumerate(list_repos, start=1):
        try:
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
                logger.error(
                    f"First commit is different from expected, forced pushed?", indent=2
                )
                output_csv.append([repo_id, repo_url, "error_forced", first_commit_main.sha])
                continue

            # check if a Feedback PR already exists (search by title, not PR number,
            # since an earlier issue/PR can shift the Feedback PR's number away from 1)
            try:
                pr_feedback = next(
                    (
                        pr
                        for pr in repo.get_pulls(state="all", sort="created", direction="asc")
                        if pr.title == args.title
                    ),
                    None,
                )
            except GithubException as e:
                logger.error(f"Unknown exception listing PRs: {e}", indent=2)
                output_csv.append([repo_id, repo_url, "exception_get_pr", e])
                continue

            if pr_feedback is not None:
                # Feedback PR already exists, check if it was merged
                if pr_feedback.merged:
                    logger.info(
                        f"PR Feedback (#{pr_feedback.number}) merged!!! {pr_feedback}",
                        indent=2,
                    )
                    output_csv.append([repo_id, repo_url, "error_merged", ""])
                else:
                    logger.info(f"Feedback PR already exists (#{pr_feedback.number}). Nothing to do.", indent=2)
                continue

            logger.info(f"No Feedback PR found in repo {repo_name}. We will create it...", indent=2)

            # HERE WE KNOW PR IS MISSING, SO WE WILL CREATE IT!

            # get the slug to @mentioning in PR text
            slug = repo_id
            repo_teams = repo.get_teams()
            if repo_teams.totalCount > 0:
                # get the first team slug
                slug = repo_teams[0].slug
                logger.info(f"Using slug {slug} for @mentioning.", indent=2)

            if args.dry_run:
                pr_message = MESSAGE_PR.format(GH_USERNAME=slug)
                logger.warning(
                    f"Dry run!!!: Would create feedback branch at SHA {base_sha[:7]} and Feedback PR with following message:\n {pr_message}",
                    indent=2,
                )
                output_csv.append([repo_id, repo_url, "dry-run", base_sha[:7]])
                continue

            # FIRST, create a feedback branch from the base SHA
            pr_branch = args.title.lower().replace(" ", "_")  # feedback
            try:
                repo.create_git_ref(f"refs/heads/{pr_branch}", base_sha)
                logger.info(
                    f"Created feedback branch '{pr_branch}' at SHA {base_sha[:7]}.", indent=2
                )
            except GithubException as e:
                if e.data["message"] == "Reference already exists":
                    logger.info(f"Branch '{pr_branch}' already exists.", indent=2)
                else:
                    logger.error(f"Error creating branch '{pr_branch}': {e}", indent=2)
                    output_csv.append([repo_id, repo_url, "exception_create_branch", e])
                    continue

            # SECOND, create a PR for feedback branch
            # there must be at least one commit in the main to be able to PR into a feedback PR - create a dummy commit otherwise
            if no_commits == 1:
                logger.warning(f"No commits in main branch yet, need to create a dummy one to create PR.", indent=2)
                keep_file = ".github/keep"
                keep_content = " "
                # Check if the file already exists
                try:
                    existing_file = repo.get_contents(keep_file)
                    # File exists – update it
                    repo.update_file(
                        path=keep_file,
                        message="Setting up Feedback PR",
                        content=keep_content,
                        sha=existing_file.sha,
                    )
                except GithubException as e:
                    if e.status == 404:
                        # File does not exist – create it
                        repo.create_file(
                            path=keep_file,
                            message="Setting up Feedback PR",
                            content=keep_content,
                        )
                    else:
                        logger.error(f"Error setting up dummy file '{keep_file}': {e}", indent=2)
                        output_csv.append([repo_id, repo_url, "exception_create_dummy_file", e])
                        continue

                logger.info(f"Dummy file {keep_file} was updated/created.", indent=2)
            # time to create the PR
            try:
                pr = repo.create_pull(
                    title=args.title,
                    body=MESSAGE_PR.format(GH_USERNAME=slug),
                    head="main",
                    base=pr_branch,    # PR from main to feedback
                )
                logger.info(
                    f"Feedback PR #{pr.number} created in repo {repo_name}: {pr.html_url}",
                    indent=2,
                )
            except GithubException as e:
                logger.error(f"Exception when creating PR in repo {repo_name}: {e}", indent=2)
                if e.data["message"] == "Validation Failed":
                    # This should not happen anymore as we create a dummy commit in main to be able to PR into feedback
                    logger.error(f"Perhaps no commits exist in repo.", indent=2)
                    output_csv.append(
                        [repo_id, repo_url, "exception_validation", e]
                    )
                else:
                    output_csv.append([repo_id, repo_url, "exception_create", e])
                continue

            # all good! PR was created SUCCESSFULLY!
            output_csv.append([repo_id, repo_url, "created", ""])

        except Exception as e:
            logger.error(f"Unexpected error processing repo {repo_name}: {e}", indent=2)
            output_csv.append([repo_id, repo_url, "exception_unexpected", e])

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
