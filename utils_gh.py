import base64
import sys
from github import Github, Auth
from github.GithubException import GithubException
from github.Repository import Repository
from typing import Optional


def read_token(token_file):
    with open(token_file, "r") as f:
        return f.read().strip()


def get_token(token_str: str, token_file: str) -> str:
    if token_str:
        return token_str.strip()
    elif token_file:
        try:
            with open(token_file, "r") as f:
                return f.read().strip()
        except Exception as e:
            print(f"❌ Failed to read token file: {e}")
            sys.exit(1)
    else:
        print("❌ You must provide either --token or --token-file")
        sys.exit(1)


def open_gitHub(token_file=None, token=None, user=None, password=None) -> Github:
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


def print_repo_info(repo: Repository):
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


def get_issue_node_id(g: Github, repo: Repository, issue_number: int) -> Optional[str]:
    """Get the GraphQL node ID for a given issue or PR, identified by its number."""
    
    try:
        # GET /repos/{owner}/{repo}/issues/{issue_number}
        response, data = g.requester.requestJsonAndCheck(
            "GET", 
            f"/repos/{repo.full_name}/issues/{issue_number}"
        )
        # Extract the global GraphQL node ID
        node_id = data['node_id']
        return node_id
    except GithubException as e:
        if e.status == 404:
            return None   # issue does not exist
        raise            # real error → propagate


def unsubscribe(g: Github, issue_node_id: str) -> dict:
    """Unsubscribe from notifications for a given issue or PR, identified by its GraphQL node ID."""
    mutation = """
    mutation($id: ID!) {
    updateSubscription(input: {subscribableId: $id, state: UNSUBSCRIBED}) {
        subscribable {
        viewerSubscription
        }
    }
    }
    """

    # Execute via requestJsonAndCheck
    response, data = g.requester.requestJsonAndCheck(
        "POST",
        "/graphql",
        input={"query": mutation, "variables": {"id": issue_node_id}},
    )

    return data


def is_subscribed(g: Github, repo: Repository, pr_number: int) -> bool:
    url = f"/repos/{repo.full_name}/issues?filter=subscribed&state=all"
    url = f"/repos/{repo.full_name}/notifications?all=true"

    print("URL:", url)
    try:
        data = g.requester.requestJsonAndCheck("GET", url)
        print(data)
        return data.get("subscribed", False)
    except GithubException as e:
        print(e)
        if e.status == 404:
            return False
        raise


def set_subscription(g: Github, thread_id: str, subscribe: bool) -> dict:
    """Set the subscription status for a given notification thread.
    
    I don't know why unsubscribing cannot be achived with {"subscribed": False} but instead requires {"ignored": True} (ignoring is stronger!)
    """
    input = {"subscribed": True} if subscribe else {"ignored": True}
    _, data = g.requester.requestJsonAndCheck(
        "PUT",
        f"/notifications/threads/{thread_id}/subscription",
        input=input,
    )
    return data


def get_subscription(g: Github, thread_id: str) -> dict:
    header, data = g.requester.requestJsonAndCheck(
        "GET",
        f"/notifications/threads/{thread_id}/subscription",
    )
    return data
