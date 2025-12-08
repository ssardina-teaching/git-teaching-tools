"""
Get or update the list of issue labels in a repository

Uses PyGithub (https://github.com/PyGithub/PyGithub) as API to GitHub:

    python3 -m pip install PyGithub

PyGithub documentation: https://pygithub.readthedocs.io/en/latest/introduction.html

Library uses REST API: https://docs.github.com/en/rest
    https://docs.github.com/en/rest/issues/labels#list-labels-for-a-repository

Some usage help on PyGithub:
    https://www.thepythoncode.com/article/using-github-api-in-python

Issue: https://github.com/ssardina-teaching/git-teaching-tools/issues/23

Example:

    $ python gh_issue_labels.py get harry-honours-2025/honours-software -t jasdlakjsdlj1223d --file labels.json

    $ python gh_issue_labels.py push harry-honours-2025/honours-software -tf  ~/.ssh/keys/gh-token-ssardina.txt --file labels.json --replace

In the ends, this is doing something equivalent to:

    $ curl -X POST -H "Authorization: token YOUR_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    https://api.github.com/repos/YOUR_ORG/YOUR_REPO/labels \
    -d '{"name":"bug", "color":"d73a4a", "description":"Something is not working"}'
"""
__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com + ChatGPT friend"
__copyright__ = "Copyright 2025"
import sys
import argparse
import json
from github import Github, Repository, Organization, GithubException, Auth
from github.GithubException import GithubException


def read_token(token_str, token_file):
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


def download_labels(repo, output_file):
    labels = []
    for label in repo.get_labels():
        labels.append(
            {
                "name": label.name,
                "color": label.color,
                "description": label.description or "",
            }
        )
    with open(output_file, "w") as f:
        json.dump(labels, f, indent=2)
    print(f"✅ Labels downloaded to {output_file}")


def push_labels(repo, input_file, replace=False):
    with open(input_file, "r") as f:
        new_labels = json.load(f)

    new_label_names = {lbl["name"] for lbl in new_labels}
    existing_labels = {label.name: label for label in repo.get_labels()}

    if replace:
        print("🧹 Checking for labels to delete...")
        for name, label in existing_labels.items():
            if name not in new_label_names:
                try:
                    label.delete()
                    print(f"❌ Deleted label: {name}")
                except GithubException as e:
                    print(f"⚠️ Could not delete label '{name}': {e}")

    # Refresh labels after deletion (important if modifying in-place)
    existing_labels = {label.name: label for label in repo.get_labels()}

    for label_data in new_labels:
        name = label_data["name"]
        color = label_data.get("color", "ffffff")
        description = label_data.get("description", "")

        try:
            if name in existing_labels:
                label = existing_labels[name]
                label.edit(name=name, color=color, description=description)
                print(f"🔄 Updated label: {name}")
            else:
                repo.create_label(name=name, color=color, description=description)
                print(f"➕ Created label: {name}")
        except GithubException as e:
            print(f"❌ Error updating/creating label '{name}': {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Download or push issue labels from/to a GitHub repo using PyGithub."
    )
    parser.add_argument("action", choices=["get", "push"], help="Action to perform")
    parser.add_argument("repo_name", help="Repository name in the format 'owner/repo'")
    parser.add_argument(
        "--token",
        "-t",
        help="GitHub personal access token (alternatively use --token-file)",
    )
    parser.add_argument(
        "--token-file", "-tf", help="File containing the GitHub personal access token"
    )
    parser.add_argument(
        "--file",
        default="labels.json",
        help="Input/output file for labels (default: labels.json)",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="When pushing: delete labels not in the file",
    )
    args = parser.parse_args()
    token = read_token(args.token, args.token_file)

    # g = Github(auth=Auth.Token(token))
    g = Github(token)
    try:
        repo = g.get_repo(args.repo_name)
    except GithubException as e:
        print(f"❌ Failed to access repository: {e}")
        sys.exit(1)

    if args.action == "get":
        download_labels(repo, args.file)
    elif args.action == "push":
        push_labels(repo, args.file, args.replace)


if __name__ == "__main__":
    main()
