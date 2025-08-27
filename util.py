import base64
import csv
import os
import shutil
from github import Github, Repository, Organization, GithubException, Auth
import git

# get the TIMEZONE to be used - ZoneInfo requires Python 3.9+
from datetime import datetime, timezone
from zoneinfo import ZoneInfo  # Python 3.9+
TIMEZONE_STR = "Australia/Melbourne"  # https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
DATE_FORMAT = "%-d/%-m/%Y %-H:%-M:%-S"  # RMIT Uni (Australia)
TIMEZONE = ZoneInfo(TIMEZONE_STR)
UTC = ZoneInfo("UTC")
NOW = datetime.now(TIMEZONE).replace(microsecond=0)
NOW_TXT = NOW.strftime("%Y-%m-%d_%H-%M")
NOW_ISO = NOW.isoformat()

LOGGING_FMT = "%(asctime)s %(levelname)-8s %(message)s"
LOGGING_DATE = "%a, %d %b %Y %H:%M:%S"
LOGGING_DATE = "%Y-%m-%d %H:%M:%S"

GH_HTTP_URL_PREFIX = "https://github.com"
GH_GIT_URL_PREFIX = "git@github.com:"
REPOS_HEADER_CSV = [
    "NO",   # 1, 2, 3, ...
    "ORG_NAME",  # RMIT-COSC2780-2973-IDM25
    "REPO_ID_PREFIX",  # workshop-6
    "REPO_ID_SUFFIX",  # ssardina
    "REPO_ID",  # workshop-6/ssardina
    "REPO_URL",  # git@github.com:RMIT-COSC2780-2973-IDM25/workshop-6/ssardina.git
    "REPO_HTTP",  # htpps://github.com/RMIT-COSC2780-2973-IDM25/workshop-6/ssardina.git
]


def timezone_time(*args):
    return datetime.now(TIMEZONE).timetuple()


def get_repos_from_csv(csv_file, repos_ids=None, ignore_ids=None) -> list[dict]:
    """
    Collect list of teams with their git URL links from a CSV file.
    Case insensitive search for the repo ids.

    :param csv_file: file where csv data is with two fields TEAM and GIT
    :param repos_ids: list of specific repo names to consider or None
    :param ignore_ids: list of specific repo names to ignore or None
    :return: a list of dictionaries for each repo (name, url, etc)
            e.g., {'ORG_NAME': 'RMIT-COSC1127-1125-AI24', 'REPO_ID_PREFIX': 'p0-warmup', 'REPO_ID_SUFFIX': 'msardina', 'REPO_ID': 'RMIT-COSC1127-1125-AI24/p0-warmup-msardina', 'REPO_URL': 'git@github.com:RMIT-COSC1127-1125-AI24/p0-warmup-msardina.git'}
    """

    # Get the list of ALL teams with their GIT URL from the CSV file
    with open(csv_file, "r") as f:
        repos = list(csv.DictReader(f, delimiter=","))

    # Add enumeration as new field NO, if not there already
    if "NO" not in repos[0]:
        for i, t in enumerate(repos):
            t["NO"] = i + 1

    # If specific team ids given, just keep those them only
    if repos_ids is not None:
        repos = [
            t
            for t in repos
            if t["REPO_ID_SUFFIX"].lower() in list(map(str.lower, repos_ids))
        ]
    if ignore_ids is not None:
        repos = [
            t
            for t in repos
            if t["REPO_ID_SUFFIX"].lower() not in list(map(str.lower, repos_ids))
        ]
    return repos


def open_gitHub(token_file=None, token=None, user=None, password=None):
    # Authenticate to GitHub
    if token:
        auth = Auth.Token(token)
        g = Github(auth=auth)
    if token_file:
        with open(token_file) as fh:
            token = fh.read().strip()
        g = Github(token)
    elif user and password:
        g = Github(user, password)
    return g


def get_tag_info(repo: git.Repo, tag_str="head"):
    """
    Returns the information of a tag in a repo. By default the head

    :param repo: the repository to search for a tag
    :param tag_str: the tag in the repo
    :return: the tag's commit time, the tag's commit, the time it was tagged
    """
    if tag_str == "head":
        commit = repo.commit()
        commit_time = datetime.fromtimestamp(
            commit.committed_date, tz=TIMEZONE
        )
        tagged_time = commit_time
    else:
        tag = next((tag for tag in repo.tags if tag.name == tag_str), None)
        # tag_commit = next((tag.commit for tag in repo.tags if tag.name == tag_str), None)
        if tag is None:
            return None, None, None
        commit = tag.commit

        commit_time = datetime.fromtimestamp(
            commit.committed_date, tz=TIMEZONE
        )
        try:
            tagged_time = datetime.fromtimestamp(
                tag.object.tagged_date, tz=TIMEZONE
            )  # if it is an annotated tag
        except:
            tagged_time = commit_time  # if it is a lightweight tag (no date stored; https://git-scm.com/book/en/v2/Git-Basics-Tagging)
        # logging.error("\t Repo {} does not have tag {}".format(repo, tag_str))

    return commit_time, commit, tagged_time
    # return commit_time.strftime(DATE_FORMAT), commit, tagged_time.strftime(DATE_FORMAT)


def get_time_now():
    return datetime.now(tz=TIMEZONE).strftime("%Y-%m-%d-%H-%M-%S")

def date_to_utc(date: datetime) -> datetime:
    """
    Convert a datetime object to UTC timezone.
    :param date: the datetime object to convert
    :return: the datetime object in UTC timezone
    """
    if date.tzinfo is None:
        date = TIMEZONE.localize(date)
    return date.astimezone(timezone.utc)


def backup_file(file_path: str, rename=False):
    if os.path.exists(file_path):
        if rename:
            os.rename(file_path, f"{file_path}-{NOW_TXT}.bak")
        else:
            shutil.copy(file_path, f"{file_path}-{NOW_TXT}.bak")


def print_repo_info(repo : Repository):
    # repository full name
    print("Full name:", repo.full_name)
    # repository description
    print("Description:", repo.description)
    # the date of when the repo was created
    print("Date created:", repo.created_at)
    # the date of the last git push
    print("Date of last push:", repo.pushed_at)
    # home website (if available)
    print("Home Page:", repo.homepage)
    # programming language
    print("Language:", repo.language)
    # number of forks
    print("Number of forks:", repo.forks)
    # number of stars
    print("Number of stars:", repo.stargazers_count)
    print("-" * 50)
    # repository content (files & directories)
    print("Contents:")
    for content in repo.get_contents(""):
        print(content)
    try:
        # repo license
        print(
            "License:", base64.b64decode(repo.get_license().content.encode()).decode()
        )
    except:
        pass

def add_csv(csv_file: str, header: list, rows: list, append=True, quoting=csv.QUOTE_MINIMAL, timestamp=None):
    # build the dictionary for each row
    dict_rows = [dict(zip(header, row)) for row in rows]
    mode = "a" if append else "w"

    if timestamp is not None:
        # add timestamp to each row
        header = header + ["TIMESTAMP"]
        for row in dict_rows:
            row["TIMESTAMP"] = timestamp

    with open(csv_file, mode) as f:
        writer = csv.DictWriter(f, fieldnames=header, quoting=quoting)

        # write header if file is empty
        if f.tell() == 0:
            writer.writeheader()

        writer.writerows(dict_rows)
