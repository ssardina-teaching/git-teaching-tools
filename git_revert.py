#!/usr/bin/env python
"""
A script to revert the repo to a previous commit.
This is useful when the student has issue way too many commits

Script takes:
    1) a CSV file with a collection of repositories;
    2) a tag to clone at (defaults to `main`)
    3) an output folder

and clones/updates the repo in an output directory. It also produces a file CSV file with the timestamps of the tag for the successful repo cloned/updated.

This script uses GitPython module gitpython to have Git API:
    https://gitpython.readthedocs.io/en/stable/tutorial.html

    $ python -m pip install gitpython

GitPython provides object model access to your git repository.
A lot of tips on using GitPython: http://www.legendu.net/misc/blog/hands-on-GitPython/

Manual debug via gitpython:

    >>> import git
    >>> repo = git.Repo("submissions/deepyellow2")
    >>> repo.common_dir
    /mnt/ssardina-volume/cosc1125-1127-AI/AI21/p-contest/preliminary/submissions/deepyellow2/.git
    >>> repo.remote()
    <git.Remote "origin">
    >>> repo.remote().exists()
    True
    >>> repo.remote('origin').fetch(tags=True,force=True)
    [<git.remote.FetchInfo object at 0x7fd4469054f0>, <git.remote.FetchInfo object at 0x7fd446905ae0>, <git.remote.FetchInfo object at 0x7fd446905a40>, <git.remote.FetchInfo object at 0x7fd4469059a0>, <git.remote.FetchInfo object at 0x7fd446905900>, <git.remote.FetchInfo object at 0x7fd446905b80>, <git.remote.FetchInfo object at 0x7fd446905c70>, <git.remote.FetchInfo object at 0x7fd446905cc0>, <git.remote.FetchInfo object at 0x7fd446905d60>, <git.remote.FetchInfo object at 0x7fd446905e50>]
    >>> repo.commit()
    <git.Commit "d859a90ef90b3212750d0f70c894995c5311b893">
    >>> repo.commit().committed_date
    1648214671
    >>> repo.git.pull()
    'Already up to date.'
"""
__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2018-2025"

import shutil
import os
import sys
import argparse
import csv
import time
import traceback

# local utilities
import util, utils_gh
from util import (
    GH_GIT_URL_PREFIX,
    TIMEZONE,
    UTC,
    NOW,
    NOW_ISO,
    NOW_TXT,
    LOGGING_DATE,
    LOGGING_FMT,
    GH_HTTP_URL_PREFIX,
)


# https://gitpython.readthedocs.io/en/stable/reference.html
# http://gitpython.readthedocs.io/en/stable/tutorial.html
import git

# from git import Repo, Git

import logging
import coloredlogs
LOGGING_LEVEL = logging.INFO
# LOGGING_LEVEL = logger.DEBUG
# logger.basicConfig(format=LOGGING_FMT, level=LOGGING_LEVEL, datefmt=LOGGING_DATE)
logger = logging.getLogger(__name__)
coloredlogs.install(level=LOGGING_LEVEL, fmt=LOGGING_FMT, datefmt=LOGGING_DATE)

TIMESTAMP_HEADER_CSV = [
        "repo",
        "submitted_at",
        "commit",
        "tag",
        "tagged_at",
        "no_commits",
        "status",
    ]


def clone_team_repos(repos:list, tag:str, output_folder:str):
    """
    Clones a the repositories from a list of repos at the tag commit into a given folder

    :param list_repos: a dictionary mapping team names to git-urls
    :param tag_str: the tag to grab
    :return: the following information as a tuple:
         repos_cloned : teams that were successfully cloned
         repos_new: teams that are new
         repos_updated: teams that were there and got a new version in the tag
         repos_unchanged: teams that were there but with the same tag version
         repos_missing: teams that where not cloned
    """
    no_repos = len(repos)
    repos.sort(key=lambda tup: tup["REPO_ID_SUFFIX"].lower())  # sort the list of teams

    logger.info(f"About to clone {no_repos} repo teams into folder {output_folder}/.")
    repos_new = []
    repos_missing = []
    repos_unchanged = []
    repos_updated = []
    repos_cloned = []
    repos_notag = []
    repos_noteam = []
    for k, row in enumerate(repos, start=1):
        repo_no = row["NO"]
        repo_http_url = row["REPO_HTTP"]
        repo_name = row["REPO_ID_SUFFIX"]
        repo_git_url = row["REPO_URL"]
        repo_local_dir = os.path.join(output_folder, repo_name)
        logger.info(
            f"Processing {k}/{no_repos} repo {repo_no}:{repo_name} at {repo_http_url} - Save to {repo_local_dir}."
        )

        time.sleep(2)
        if not os.path.exists(
            repo_local_dir
        ):  # if there is NOT already a local repo for the team - clone from scratch!
            logger.info(f"\t Trying to clone NEW team repo from URL {repo_git_url}.")
            try:
                repo = git.Repo.clone_from(repo_git_url, repo_local_dir, branch=tag)
                new_commit_time, new_commit, new_tagged_time = util.get_tag_info(
                    repo, tag_str="head"
                )
                logger.info(
                    f"\t Repo {repo_name} cloned successfully with tag date {new_commit_time}."
                )
                repos_new.append(repo_name)
                status = "new"
            except git.GitCommandError as e:
                repos_missing.append(repo_name)
                logger.warning(
                    f"Repo {repo_name} with tag/branch {tag} cannot be cloned: {e.stderr}"
                )
                continue
            except KeyboardInterrupt:
                logger.warning(
                    "Script terminated via Keyboard Interrupt; finishing..."
                )
                sys.exit("keyboard interrupted!")
            except TypeError as e:
                logger.warning(
                    f"Repo {repo_name} was cloned but has no tag {tag}, removing it...: {e}"
                )
                repo.close()
                shutil.rmtree(repo_local_dir)
                repos_notag.append(repo_name)
                continue
            except Exception as e:
                logger.error(
                    f"Repo {repo_name} cloned but unknown error when getting tag {tag}; should not happen. Stopping... {e}"
                )
                repo.close()
                exit(1)
        else:  # OK, so there is already a directory for this team in local repo, check if there is an update
            try:
                # First get the timestamp of the local repository for the team
                repo = git.Repo(
                    repo_local_dir
                )  # https://gitpython.readthedocs.io/en/stable/reference.html#module-git.repo.base

                # get date of local head commit (where the local repo is pointing to)
                local_commit_time, _, _ = util.get_tag_info(repo, tag_str="head")

                logger.info(
                    f"\t Existing LOCAL submission for {repo_name} dated {local_commit_time} ({str(repo.commit())[:7]}); updating it..."
                )

                # Next, first fetch from remote all tags and new commits
                # As of Git 2.2, we need to force to allow overwriting existint tags!
                # https://gitpython.readthedocs.io/en/stable/reference.html#git.remote.Remote.fetch
                repo.remote("origin").fetch(tags=True, force=True)

                if tag in ["master", "main"]:
                    repo.git.checkout(tag, force=True)
                    repo.git.pull()
                    new_commit_time, new_commit, new_tagged_time = util.get_tag_info(
                        repo, tag_str="head"
                    )
                else:
                    new_commit_time, new_commit, new_tagged_time = util.get_tag_info(
                        repo, tag
                    )
                    if (
                        new_commit_time is None
                    ):  # tag has been deleted! remove local repo, no more submission
                        repos_missing.append(repo_name)
                        logger.info(
                            f"No tag {tag} in the repository for team {repo_name} anymore; removing it..."
                        )
                        repo.close()
                        shutil.rmtree(repo_local_dir)
                        continue
                    # Checkout the submission tag (doesn't matter if there is no update, will stay as is)
                    repo.git.checkout(tag)

                logger.debug(
                    f"Tag *{tag}* seen in in commit {str(new_commit)[:7]} ({new_commit_time}) tagged on {new_tagged_time}"
                )

                # Now process timestamp to report new or unchanged repo
                if new_commit_time == local_commit_time:
                    logger.info(f"Team {repo_name} submission has not changed.")
                    repos_unchanged.append(repo_name)
                    status = "unchanged"
                else:
                    logger.info(
                        f"Team {repo_name} updated successfully with new tag date {new_commit_time}"
                    )
                    repos_updated.append(repo_name)
                    status = "updated"
            except git.GitCommandError as e:
                repos_missing.append(repo_name)
                logger.warning(
                    f"Problem with existing Repo {repo_name}; removing it: {e} - {e.stderr}"
                )
                print("\n")
                repo.close()
                continue
            except KeyboardInterrupt:
                logger.warning(
                    "Script terminated via Keyboard Interrupt; finishing..."
                )
                repo.close()
                sys.exit(1)
            except:  # catch-all
                print(traceback.print_exc())
                exit(1)

                repos_missing.append(repo_name)
                logger.warning(
                    f"\t Local repo {repo_local_dir} is problematic; removing it..."
                )
                print(traceback.print_exc())
                print("\n")
                repo.close()
                shutil.rmtree(repo_local_dir)
                continue

        # this just calls git rev-list --count /tags/<tag> to get the number of commits tracing to the tag
        try:
            no_commits = repo.git.rev_list(
                "--count", tag
            )  # get the no of commits tracing to the tag
        except git.exc.GitCommandError:
            no_commits = repo.git.rev_list(
                "--count", f"tags/{tag}"
            )  # get the no of commits tracing to the tag
        repo.close()
        # Finally, write teams that have repos (new/updated/unchanged) into submission timestamp file
        repos_cloned.append(
            {
                "repo": repo_name,
                "submitted_at": new_commit_time.strftime(util.DATE_FORMAT),
                "commit": new_commit,
                "tag": tag,
                "tagged_at": new_tagged_time.strftime(util.DATE_FORMAT),
                "no_commits": no_commits,
                "status": status,
            }
        )

    # the end....
    return (
        repos_cloned,
        repos_new,
        repos_updated,
        repos_unchanged,
        repos_missing,
        repos_notag,
        repos_noteam,
    )


def report_teams(type, teams):
    """
    Print the name of the teams for the class type

    :param type: string with the name of the class (new, updated, missing, etc.)
    :param teams: a list of team names
    :return:
    """
    print(f"{type}: {len(teams)}")
    for t in teams:
        print(f"\t {t}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Clone a list of GIT repositories containing assignment submissions via a tag."
    )
    parser.add_argument(
        dest="REPO_FOLDER",
        type=str,
        help="Repo to revert.",
    )
    parser.add_argument(
        dest="COMMIT",
        type=str,
        help="Commit to revert back to.",
    )
    parser.add_argument(
        "--keep",
        nargs="+",
        help="Paths to keep and do not revert back.",
    )
    parser.add_argument(
        "--yes",
        default=False,
        action="store_true",
        help="Do not alsk for confirmation (Default: %(default)s).",
    )
    # we could also use vars(parser.parse_args()) to make args a dictionary args['<option>']
    args = parser.parse_args()
    logger.info(f"Starting script on {TIMEZONE}: {NOW_ISO} - {args}")

    ###############################################
    # Validation checks
    ###############################################
    if not os.path.exists(args.REPO_FOLDER):
        print(f"Repo CSV database {args.REPO_FOLDER} does not exists!")
        exit(1)

    ###############################################
    # Get repos as desired
    ###############################################

    repo = git.Repo(args.REPO_FOLDER)
    head_sha = repo.head.commit.hexsha
    # Check if the repo is valid
    if repo.bare:
        logger.error(f"Repo {args.REPO_FOLDER} is not a valid repo!")
        exit(1)

    try:
        logger.info(
            f"Reverting repo {args.REPO_FOLDER} to commit {args.COMMIT} except {args.keep}"
        )
        repo.git.revert(f"{args.COMMIT}..HEAD", no_commit = True)
        for f in args.keep:
            repo.git.restore("--staged", "--worktree", f)

        logger.info("This is how it looks after reverting:")
        print(repo.git.status())
        if not args.yes:
            answer = input("Are you sure you want to revert the repo? (y/N): ")
            if answer.lower() != "y":
                print("Aborting...")
                exit(0)
        logger.info(f"Contunue the revert...")
        repo.git.revert("--continue")

        repo.git.log("--graph", "--pretty='%Cred%h%Creset -%C(auto)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --all")
        if not args.yes:
            answer = input("Are you sure you want to revert the repo? (y/N): ")
            if answer.lower() != "y":
                print("Aborting...")
                exit(0)
        logger.info(f"Pushing reverted repo {args.REPO_FOLDER} to remote.")            
        repo.git.push()
    except git.GitCommandError as e:
        logger.error(f"Error reverting repo {args.REPO_FOLDER} to commit {args.COMMIT}: {e}")
        logger.info(f"Reverting back to commits: {head_sha}")
        repo.git.reset("--hard", f"{head_sha}")
