#!/usr/bin/env python
"""
Remove a list of GitHub usernames from a GitHub Classroom50 class, and
optionally from the underlying GitHub organization, using the `gh teacher`
CLI extension.

The underlying command only removes one username at a time:

    $ gh teacher roster remove ORG CLASSROOM USERNAME

For example:

    $ gh teacher roster remove RMIT-COSC1127-3117-AI ai26 kingfish-sith
    RMIT-COSC1127-3117-AI/classroom50/ai26/roster.csv: removed kingfish-sith (org membership unchanged)
    RMIT-COSC1127-3117-AI: removed kingfish-sith from classroom team classroom50-ai26
      to also remove kingfish-sith from the org: gh teacher remove RMIT-COSC1127-3117-AI kingfish-sith

This script loops that call over a whole list of usernames, given either as
extra command-line arguments or via a CSV file with a "username" header
column (-c/--csv). If --remove-org is given, it also runs, as suggested by
the output above, for every username:

    $ gh teacher remove ORG USERNAME

to fully remove the username from the organization too (not just the
classroom team).

Requires the `gh` CLI, authenticated, with the `teacher` extension installed.

Example:

    $ python gh_roster_remove.py RMIT-COSC1127-3117-AI ai26 kingfish-sith foo-bar
    $ python gh_roster_remove.py RMIT-COSC1127-3117-AI ai26 --csv drop_list.csv --remove-org
    $ python gh_roster_remove.py RMIT-COSC1127-3117-AI ai26 --csv drop_list.csv --dry-run

Errors and successful removals are appended (timestamped) to
roster_remove_errors.csv and roster_removed.csv respectively.
"""
__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2024-2026"

import csv
import subprocess
import sys
from argparse import ArgumentParser

from util import NOW_TXT, TIMEZONE, add_csv

SCRIPT_NAME = "gh_roster_remove"


# setup my own logger for this script, using the slogger/loguru backend
from slogger.loguru_backend import logger, setup_logger

setup_logger(source=SCRIPT_NAME, timezone=TIMEZONE.key)


CSV_ERRORS = "roster_remove_errors.csv"
CSV_ERRORS_HEADER = ["USERNAME", "STAGE", "ERROR"]

CSV_REMOVED = "roster_removed.csv"
CSV_REMOVED_HEADER = ["USERNAME", "ORG", "CLASSROOM"]


def load_usernames_csv(file_path: str, col_key: str = "username") -> list[str]:
    """
    Load the list of usernames from a CSV file with a `col_key` header column.
    """
    usernames = []
    with open(file_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or col_key not in [
            h.strip() for h in reader.fieldnames
        ]:
            logger.error(
                f'CSV file "{file_path}" has no "{col_key}" header column.'
            )
            sys.exit(1)
        for row in reader:
            username = (row.get(col_key) or "").strip()
            if username:
                usernames.append(username)
    return usernames


def run_gh(*args: str, dry_run: bool = False) -> tuple[bool, str]:
    """
    Run a `gh` CLI command; return (success, combined stdout/stderr text).
    """
    cmd = ["gh", *args]
    if dry_run:
        print(f"[DRY-RUN] {' '.join(cmd)}")
        return True, ""

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Remove a list of GitHub usernames from a GitHub Classroom "
        "classroom (and optionally from the organization) via the `gh teacher` CLI."
    )
    parser.add_argument("ORG", help="GitHub organization name.")
    parser.add_argument("CLASSROOM", help="Classroom name within the organization.")
    parser.add_argument(
        "USERNAMES", nargs="*", help="GitHub usernames to remove."
    )
    parser.add_argument(
        "-c",
        "--csv",
        metavar="FILE",
        help='CSV file with a "username" header column listing usernames to remove.',
    )
    parser.add_argument(
        "--remove-org",
        action="store_true",
        default=False,
        help="Also remove each username from the GitHub organization "
        "(gh teacher remove ORG USERNAME) (Default: %(default)s).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print the gh commands instead of running them (Default: %(default)s).",
    )
    args = parser.parse_args()
    logger.info(f"Starting on {TIMEZONE}: {NOW_TXT}")

    usernames = list(args.USERNAMES)
    if args.csv:
        usernames += load_usernames_csv(args.csv)

    # keep order but drop duplicates
    usernames = list(dict.fromkeys(usernames))

    if not usernames:
        logger.error(
            "No usernames given, either as arguments or via --csv. Stopping."
        )
        sys.exit(1)

    logger.info(
        f"Removing {len(usernames)} user(s) from classroom '{args.CLASSROOM}' "
        f"in org '{args.ORG}' (remove-org={args.remove_org}, dry-run={args.dry_run})"
    )

    errors_csv = []
    removed_csv = []
    removed_class = 0
    removed_org = 0
    for username in usernames:
        logger.info(f"----> {username}")
        ok, output = run_gh(
            "teacher", "roster", "remove", args.ORG, args.CLASSROOM, username,
            dry_run=args.dry_run,
        )
        if output:
            print(output)
        if not ok:
            logger.error(f"\t Failed to remove {username} from classroom roster.")
            errors_csv.append([username, args.ORG, args.CLASSROOM])
            continue
        removed_csv.append([username, args.ORG, args.CLASSROOM])
        removed_class += 1

        org_removed = False
        if args.remove_org:
            ok, output = run_gh(
                "teacher", "remove", args.ORG, username, dry_run=args.dry_run
            )
            if output:
                print(output)
            if not ok:
                logger.error(f"\t Failed to remove {username} from organization.")
                errors_csv.append([username, args.ORG, ""])
                continue
            removed_csv.append([username, args.ORG, ""])
            removed_org += 1

    logger.info(
        f"Finished! Total usernames: {len(usernames)} - Removed from roster/org: {removed_class}/{removed_org} - Errors: {len(errors_csv)}."
    )

    if not args.dry_run:
        add_csv(
            CSV_ERRORS,
            CSV_ERRORS_HEADER,
            errors_csv,
            append=True,
            timestamp=NOW_TXT,
        )
        add_csv(
            CSV_REMOVED,
            CSV_REMOVED_HEADER,
            removed_csv,
            append=True,
            timestamp=NOW_TXT,
        )
        logger.info(f"Removed users written to {CSV_REMOVED}.")
        if errors_csv:
            logger.info(f"Errors written to {CSV_ERRORS}.")

    if errors_csv:
        sys.exit(1)
