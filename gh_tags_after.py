"""
Get the repos that were tagged after a given date

Uses PyGithub (https://github.com/PyGithub/PyGithub) as API to GitHub:

    python3 -m pip install PyGithub

PyGithub documentation: https://pygithub.readthedocs.io/en/latest/introduction.html

Library uses REST API: https://docs.github.com/en/rest

Some usage help on PyGithub:
    https://www.thepythoncode.com/article/using-github-api-in-python

Example:

    $  python ./tools/git-teaching-tools.git/gh_tags_after.py repos.csv submission -t ~/.ssh/keys/gh-token-ssardina.txt --since 2025-10-07T15:30
"""
__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2024-2025"
import csv
from argparse import ArgumentParser
import time
from datetime import datetime
import util
# https://pygithub.readthedocs.io/en/latest/introduction.html

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


SCRIPT_NAME = "gh_tag_after"

import logging
from slogger import setup_logging
logger = setup_logging(SCRIPT_NAME, rotating_file="app.log", indent=2)
logger.setLevel(logging.INFO)  # set the level of the application logger
logging.root.setLevel(logging.WARNING)  # root logger above info: no 3rd party logs



#####################################
# LOCAL GLOBAL VARIABLES FOR SCRIPT
#####################################
OUT_CSV = f"tags-repos-{NOW_TXT}.csv"
HEADER_CSV = ["REPO_ID_SUFFIX", "TAG", "COMMIT", "DATE"]

SLEEP_RATE = 10  # number of repos to process before sleeping
SLEEP_TIME = 5  # sleep time in seconds between API calls


if __name__ == "__main__":
    parser = ArgumentParser(description="Handle automarking workflows")
    parser.add_argument("REPO_CSV", help="List of repositories to get data from.")
    parser.add_argument("TAG", help="Tag to look for.")
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
        "--since",
        type=str,
        default="2000-01-01T00:00",
        help="Get tags after this this date. Datetime in ISO format, e.g., 2025-04-09T15:30.",
    )
    parser.add_argument(
        "--until",
        type=str,
        help="Get tags before this date. Datetime in ISO format, e.g., 2025-04-09T15:30.",
    )
    args = parser.parse_args()
    logger.info(f"Starting script {SCRIPT_NAME} on {TIMEZONE}: {NOW_ISO}")
    logger.info(args, depth=1)

    ###############################################
    # Filter repos as desired
    ###############################################
    # Get the list of TEAM + GIT REPO links from csv file
    repos = util.get_repos_from_csv(args.REPO_CSV, args.repos)
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
        f"Getting tags between from {since_dt.isoformat()} until {until_dt.isoformat()}"
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

        # Retrieve all tags (this is usually a paginated list)
        tags = list(repo.get_tags())
        
        # Try to find your tag
        tag = next((t for t in tags if t.name == args.TAG), None)
        if tag:
            commit = tag.commit
            tag_date = commit.commit.author.date.astimezone(TIMEZONE)
            
            if not (since_dt <= tag_date <= until_dt):
                logger.warning(f"⛔ Tag '{args.TAG}' found but outside date range ({tag_date}).", depth=1)
                continue
            
            tag_sha = commit.sha[:7]
            tag_author = commit.commit.author.name
            tag_name = tag.name            
            logger.info(f"✅ Found tag '{tag_name}' on commit {tag_sha} with commit date {tag_date}", depth=1)

            output_csv.append(
                    {
                        "REPO_ID_SUFFIX": repo_id,
                        "TAG": tag_name,
                        "COMMIT": tag_sha,
                        "DATE": tag_date.isoformat(),
                    }
                )
        else:
            logger.warning(f"⛔ Tag '{args.TAG}' not found.", depth=1)
            continue
   
    # Write output_csv to a CSV file
    with open(OUT_CSV, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=HEADER_CSV,
            # delimiter="\t",
            # quoting=csv.QUOTE_NONNUMERIC,
        )
        writer.writeheader()
        writer.writerows(output_csv)
    logger.info(
        f"Finished! No of repos processed: {no_repos} - Found: {no_found} - Output written to {OUT_CSV}"
    )
