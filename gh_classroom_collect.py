#!/user/bin/env python
"""
Script to obtain all the repositories from a GitHub Classroom

Uses PyGithub (https://github.com/PyGithub/PyGithub) as API to GitHub:

    python3 -m pip install PyGithub

Some usage help on PyGithub:
    https://www.thepythoncode.com/article/using-github-api-in-python
"""
__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2019-2025"
import csv
import re
import traceback

from argparse import ArgumentParser
from github import GithubException
import os

import util
from util import (
    REPOS_HEADER_CSV,
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
# LOGGING_LEVEL = logger.DEBUG
# logger.basicConfig(format=LOGGING_FMT, level=LOGGING_LEVEL, datefmt=LOGGING_DATE)
logging.Formatter.converter = util.timezone_time
logger = logging.getLogger(__name__)
coloredlogs.install(level=LOGGING_LEVEL, fmt=LOGGING_FMT, datefmt=LOGGING_DATE)

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
        "--token",
        default=os.environ.get("GHTOKEN"),
        help="File containing GitHub authorization token/password. Defaults to GHTOKEN env variable.",
    )
    parser.add_argument(
        "-t",
        "--token-file",
        help="File containing GitHub authorization token/password.",
    )
    parser.add_argument(
        "-m",
        "--student-map",
        help=f"CSV file mapping repo suffix ({CSV_GITHUB_USERNAME}) to "
        f"student ids ({CSV_GITHUB_IDENTIFIER}).",
    )
    args = parser.parse_args()
    print(args)
    print(f"Running the script on: {util.get_time_now()}", flush=True)

    REPO_URL_PATTERN = re.compile(
        r"^{}/{}-(.*)$".format(args.ORG_NAME, args.REPO_ID_PREFIX)
    )

    ###############################################
    # Authenticate to GitHub
    ###############################################
    if not args.token_file and not args.token:
        logger.error(
            "No token or token file for authentication provided, quitting...."
        )
        exit(1)
    try:
        g = util.open_gitHub(token=args.token, token_file=args.token_file)
    except:
        logger.error(
            "Something wrong happened during GitHub authentication. Check credentials."
        )
        exit(1)

    # If --student-map is given, then it is an individual assignment and a mapping should be given
    # with columns identifier and github_username (the suffix of repos)
    user_to_id_map = dict()
    if args.student_map:
        with open(args.student_map, "r") as file:
            csv_content = csv.DictReader(file)
            for row in csv_content:
                row = dict(row)
                user_to_id_map[row[CSV_GITHUB_USERNAME]] = row[CSV_GITHUB_IDENTIFIER]
    else:
        logger.info(
            "No GitHub individual mapping provided. Team assignment; using suffix repo as identifier."
        )

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
            if args.student_map:
                if row["REPO_ID_SUFFIX"] in user_to_id_map.keys():
                    row["REPO_ID_SUFFIX"] = user_to_id_map[row["REPO_ID_SUFFIX"]]
                else:
                    logger.warning(
                        f"Repo {row['REPO_ID']} with suffix {row['REPO_ID_SUFFIX']} has no mapping. Using suffix directly."
                    )
            row['NO'] = k
            row["ORG_NAME"] = args.ORG_NAME
            row["REPO_ID_PREFIX"] = args.REPO_ID_PREFIX
            row["REPO_ID_SUFFIX"] = row["REPO_ID_SUFFIX"].lower()
            csv_writer.writerow(row)
