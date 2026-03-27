# https://pygithub.readthedocs.io/en/latest/introduction.html
from github import Github, Repository, Organization, GithubException
import util, utils_gh
import re

ORG_NAME = "RMIT-COSC1127-1125-AI21"
PREFIX = "p2"

REPO_URL_PATTERN = re.compile(r'^{}/{}-(.*)$'.format(ORG_NAME, PREFIX))


g = utils_gh.open_gitHub(token_file='/home/ssardina/.ssh/keys/gh-token-ssardina.txt')
org = g.get_organization(ORG_NAME)

org_repos = org.get_repos()


repos = []
for repo in org_repos:
    match = re.match(REPO_URL_PATTERN, repo.full_name)
    if match:
        # repo_url = 'git@github.com:{}'.format(repo.full_name)
        print(f'Found repo {repo.full_name}')
        repos.append({'REPO_SUFFIX': match.group(1), 'REPO_ID': repo.full_name, 'REPO_URL': repo.ssh_url})
        for c in repo.get_collaborators():
            if c.login not in ["AndrewPaulChester", "andresjarami", "ssardina"]:
                print(f"\tRemoving access in {repo.full_name} for user {c.login}")
                repo.remove_from_collaborators(c)

print(f"Number of repos found with prefix *{PREFIX}*:", len(repos))


#  remove_from_collaborators(collaborator)

