from github import Github, Auth
from github.GithubException import GithubException
import requests
import time

TOKEN = None  # set in main


def read_token(token_file):
    with open(token_file, "r") as f:
        return f.read().strip()


def open_gitHub(token_file=None, token=None, user=None, password=None):
    # Authenticate to GitHub
    if token:
        auth = Auth.Token(token)
        g = Github(auth=auth)
    elif token_file:
        token = read_token(token_file)
        g = Github(token)
    elif user and password:
        g = Github(user, password)
    else:
        raise Exception("No authentication provided, quitting....")
    return g


def parse_full_repo(name: str):
    """
    Parse 'org/repo' into (org, repo).
    """
    if "/" not in name:
        raise argparse.ArgumentTypeError("Repository must be in format 'org/repo'")
    org, repo = name.split("/")
    return org, repo


#######################################
# GitHub GraphQL API helper functions
#######################################

def run_query(query, variables=None):
    """Generic function to execute GraphQL queries.
        https://docs.github.com/en/graphql/overview/about-the-graphql-api
    """
    HEADERS = {"Authorization": f"bearer {TOKEN}"}
    URL = "https://api.github.com/graphql"

    query = {"query": query, "variables": variables}
    response = requests.post(
        URL, json=query, headers=HEADERS
    )
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Query failed: {response.status_code}. {response.text}")


def get_repository_node_id(owner, name):
    """Fetches the unique Node ID for a repository."""
    query = """
    query GetRepositoryNodeId($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) { id }
    }
    """
    result = run_query(query, {"owner": owner, "name": name})
    return result["data"]["repository"]["id"]


def get_issues(owner, name, closed=False):
    """Fetches a list of all open issue Node IDs from the source repo."""
    if not closed:
        query = """
        query($owner: String!, $name: String!) {
        repository(owner: $owner, name: $name) {
            issues(states: OPEN, first: 100) {
            nodes {
                id
                number
                title
            }
            }
        }
        }
        """
    else:
        query = """
        query($owner: String!, $name: String!) {
        repository(owner: $owner, name: $name) {
            issues(first: 100) {
            nodes {
                id
                number
                title
                state
            }
            }
        }
        }
        """
    result = run_query(query, {"owner": owner, "name": name})
    return result["data"]["repository"]["issues"]["nodes"]
