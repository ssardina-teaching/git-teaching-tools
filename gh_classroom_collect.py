#!/user/bin/env python
"""
Script to obtain all the repositories from a GitHub Classroom

Uses PyGithub (https://github.com/PyGithub/PyGithub) as API to GitHub:

    python3 -m pip install PyGithub

Some usage help on PyGithub:
    https://www.thepythoncode.com/article/using-github-api-in-python

Example usage:

    $ python gh_classroom_collect.py RMIT-COSC1127-3117-AI ai26-p0-warmup repos.csv
"""

__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2019-2026"
import csv
import re
import traceback

from argparse import ArgumentParser
from github import GithubException
import os

import utils_gh
from util import (
    REPOS_HEADER_CSV,
    TIMEZONE,
    NOW_ISO,
)
SCRIPT_NAME = "collect"
LOG_LEVEL = "INFO"

"""
Logging configuration

There are two ways:

    1. use my own slogger module (https://github.com/ssardina/slogger) that extends luguru and provides indentation and other features.
    2. use loguru directly, but then you have to manually add indentation and other features.
    
Both provide logger object but indentation is different:
    1. logger.info("message", depth=2)  
    2. logger.bind(depth=2).info("message")   or logger.bind(indent=2).info("message")
"""
############# OPTION 1: via slogger (NOT USED ANYMORE WITH LOGGER v2.0)
# from slogger.loguru_backend import logger, setup_logging
# setup_logging(
#     name=SCRIPT_NAME,
#     level=LEVEL,
#     colorize=True,
#     short_levels=True,
#     indent=2,
#     flush=False,
# )
# logger.remove(0)  # Remove default logger to prevent duplicate logs.

############# OPTION 2: via loguru directly + configuration
from slogger.loguru_backend import Slogger
logger = Slogger(source=SCRIPT_NAME, timezone=TIMEZONE.key)

CSV_GITHUB_USERNAME = "github_username"
CSV_GITHUB_IDENTIFIER = "identifier"

if __name__ == "__main__":
    parser = ArgumentParser(
        description="Extract repos in a GitHub Classroom repositories for a given assignment into a CSV file"
        "CSV HEADERS: ORG_NAME, REPO_ID_PREFIX, REPO_ID_SUFFIX, REPO_ID, REPO_GIT"
    )
    parser.add_argument("ORG_NAME", help="Organization name for GitHub Classroom")
    parser.add_argument("REPO_ID_PREFIX", help="Prefix string for the assignment.")
    parser.add_argument("CSV", help="CSV file where to store the set of repo links.")
    parser.add_argument(
        "-t",
        "--token",
        # default=os.environ.get("GHTOKEN") or os.environ.get("GH_TOKEN"),
        help="File or string containing GitHub authorization token/password.",
    )
    args = parser.parse_args()
    logger.info(f"Starting script {SCRIPT_NAME} on {TIMEZONE}: {NOW_ISO}")
    logger.info(args, depth=1)

    REPO_URL_PATTERN = re.compile(
        r"^{}/{}-(.*)$".format(args.ORG_NAME, args.REPO_ID_PREFIX)
    )

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
    # START WORK
    ###############################################
    logger.info(
        "Dumping repos in organization *{}* for assignment *{}* into CSV file *{}*.".format(
            args.ORG_NAME, args.REPO_ID_PREFIX, args.CSV
        )
    )

    # Get the repos of the organization and extract the ones matching the assignment prefix
    try:
        org = g.get_organization(args.ORG_NAME)
        org_repos = org.get_repos()
    except GithubException as e:
        logger.error(
            "There was an error trying to get the repos for organization {} "
            "(is the organization spelled correctly?): {}".format(args.ORG_NAME, e.data)
        )
        traceback.print_exc()
        exit(1)

    # collect all repos in the organization with the assignment prefix
    repos_select = []
    count = 0
    for repo in org_repos:
        match = re.match(REPO_URL_PATTERN, repo.full_name)
        if match:
            # repo_url = 'git@github.com:{}'.format(repo.full_name)
            count += 1
            logger.info(f"Found repo {repo.full_name}")
            repos_select.append(
                {
                    "REPO_ID_SUFFIX": match.group(1),
                    "REPO_ID": repo.full_name,
                    "REPO_URL": repo.ssh_url,
                    "REPO_HTTP": repo.html_url,
                }
            )
    logger.info(f"Number of repos found with prefix '{args.REPO_ID_PREFIX}': {count}")

    # Produce CSV file output with all repos if requested via option --csv
    logger.info(f"List of repos will be saved to CSV file: {args.CSV}")
    with open(args.CSV, "w") as output_csv_file:
        csv_writer = csv.DictWriter(
            output_csv_file,
            fieldnames=REPOS_HEADER_CSV,
        )
        csv_writer.writeheader()

        repos_select.sort(key=lambda tup: tup["REPO_ID_SUFFIX"].lower())  # sort the list of teams
        # for each repo in repo_select produce a row in the CSV file, add the team name from mapping
        for k, row in enumerate(repos_select, start=1):
            # if there is a mapping from a repo suffix to a REPO_ID_SUFFIX, do it; otherwise use SUFFIX directly
            row['NO'] = k
            row["ORG_NAME"] = args.ORG_NAME
            row["REPO_ID_PREFIX"] = args.REPO_ID_PREFIX
            row["REPO_ID_SUFFIX"] = row["REPO_ID_SUFFIX"].lower()
            csv_writer.writerow(row)
