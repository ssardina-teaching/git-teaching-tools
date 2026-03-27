#!/user/bin/env python
"""
Script to add/remove a user from GH teams in an organization
(e.g., to add tutors to groups so they can see student repos).

Uses PyGithub (https://github.com/PyGithub/PyGithub) as API to GitHub:

    python3 -m pip install PyGithub

Some usage help on PyGithub:
    https://www.thepythoncode.com/article/using-github-api-in-python
"""
__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2024"

import os
import logging
import datetime
import pytz

from argparse import ArgumentParser

import util, utils_gh

CSV_GITHUB_USERNAME = "github_username"
CSV_GITHUB_IDENTIFIER = "identifier"

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%a, %d %b %Y %H:%M:%S",
)


DATE_FORMAT = "%-d/%-m/%Y %-H:%-M:%-S"  # RMIT Uni (Australia)
TIMEZONE = pytz.timezone("Australia/Melbourne")


def get_time_now():
    return datetime.datetime.now(tz=TIMEZONE).strftime("%Y-%m-%d-%H-%M-%S")


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Add a username to a list of teams in an organization"
    )
    parser.add_argument("ORG_NAME", help="Organization name for GitHub Classroom")
    parser.add_argument("USERNAME", help="Prefix string for the assignment.")
    parser.add_argument("-u", "--user", help="GitHub username.")
    parser.add_argument(
        "-t",
        "--token",
        default=os.environ["GHTOKEN"] if os.environ["GHTOKEN"] is not None else None,
        help="File containing GitHub authorization token/password. Defaults to GHTOKEN env variable.",
    )
    parser.add_argument(
        "-tf",
        "--token-file",
        help="File containing GitHub authorization token/password.",
    )
    parser.add_argument("-p", "--password", help="GitHub username's password.")
    parser.add_argument(
        "--teams", nargs="+", help="Teams to add the user (white list)."
    )
    parser.add_argument(
        "--nteams", nargs="+", help="Teams NOT to add the user to (black list)."
    )
    parser.add_argument(
        "-d",
        "--delete",
        action="store_true",
        default=False,
        help="Remove the user from the teams, otherwise add (Default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Do not do any actual changes, run in dry-run mode (Default: %(default)s)",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        default=False,
        help="Just list the teams available; nothing more (Default: %(default)s)",
    )
    args = parser.parse_args()
    print(args)
    print(f"Running the script on: {get_time_now()}", flush=True)

    if not args.token_file and not args.token and not (args.user or args.password):
        logging.error("No authentication provided, quitting....")
        exit(1)
    try:
        g = utils_gh.open_gitHub(
            token=args.token,
            token_file=args.token_file,
            user=args.user,
            password=args.password,
        )
    except Exception:
        logging.error("Something went wrong during GitHub authentication.")
        exit(1)

    logging.info(f"Getting organization {args.ORG_NAME}...")
    org = g.get_organization(args.ORG_NAME)

    logging.info(f"Getting GH user for {args.USERNAME}...")
    user = g.get_user(args.USERNAME)

    # collect and list all teams
    teams = []
    for t in org.get_teams():
        teams.append(t.name)
    print(f"Teams available: {len(teams)}", teams)
    if args.list:
        exit(0)

    # go through all the teams and add/delete user from them as needed
    # https://pygithub.readthedocs.io/en/stable/github_objects/Organization.html#github.Organization.Organization.get_teams
    for t in org.get_teams():
        if args.nteams and t.name in args.nteams:
            continue
        if not args.nteams and args.teams and t.name not in args.teams:
            continue
        if not args.delete:
            print(f"Adding user **{args.USERNAME}** to team {t.name}")
            if not args.dry_run:
                t.add_membership(user, role="member")
        else:
            print(f"Deleting user **{args.USERNAME}** to team {t.name}")
            if not args.dry_run:
                t.remove_membership(user)
