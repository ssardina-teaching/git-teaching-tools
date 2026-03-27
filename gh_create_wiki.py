"""
Script to push a Wiki template to repos in a CSV file

 $ python3 gh_create_wiki.py ../ai20-contest-repos.csv ~/AI20/assessments/project-contest/updated-src/wiki-template/

Uses GitPython https://gitpython.readthedocs.io/en/stable/index.html
"""
__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2019-2022"

import os
import shutil

from argparse import ArgumentParser
import git
import util, utils_gh


WIKI_DIR = 'wiki'

REPOS_EXCEPT = []
# REPOS_EXCEPT = ['math-club-2',
#                 'jsj-2020-contest',
#                 'crackman',
#                 'tupacman2',
#                 'chaino1'
#                 'threelittlebirds2',
#                 'ai-jr-rw2',
#                 'mitsubishi-lancer-evolution-x',
#                 'compulsive-eater-ghost-triad2',
#                 'loginquitas-duo',
#                 'alphabetagamma']

if __name__ == '__main__':
    parser = ArgumentParser(
        description="Push a template Wiki in GitHib Wiki pages form a list of repos")
    parser.add_argument(
        'REPO_CSV', help="List of repositories to push a Wiki template.")
    parser.add_argument(
        'WIKI_TEMPLATE', help='folder where the wiki template is located.')
    parser.add_argument(
        '--repos', '--teams',
        nargs='+',
        help='if given, only the team specified will be cloned/updated.')
    parser.add_argument('--force', action='store_true',
                        help='push it even if there exists a Wiki with commits.')
    args = parser.parse_args()

    # Get the list of TEAM + GIT REPO links from csv file
    list_repos = util.get_repos_from_csv(args.REPO_CSV, args.repos)

    if len(list_repos) == 0:
        print(f'No repos found in the mapping file "{args.REPO_CSV}". Stopping.')
        exit(0)


    # Process each repo in list_repos
    # push wiki template if
    for r in list_repos:
        print(f'*** Processing repo {r["REPO_ID"]}')

        # get the specific link for the Wiki
        wiki_repo = f'git@github.com:{r["REPO_ID"]}.wiki.git'
        print(f'\t*** Wiki name: {wiki_repo}')

        # fresh clone of student wiki repo into folder WIKI_DIR/
        if os.path.exists(WIKI_DIR):
            shutil.rmtree(WIKI_DIR)
        repo = git.Repo.clone_from(wiki_repo, WIKI_DIR)

        commits = list(repo.iter_commits("master", max_count=5))

        #  should we skip the repo?
        skip = len(commits) > 1
        # skip = len(commits) > 1 or first_commit_name != 'Sebastian Sardina'
        
        if args.force or not skip:
            os.system(f"cp -rf {args.WIKI_TEMPLATE}/* {WIKI_DIR}/")
            repo.index.add(['*'])
            repo.index.commit('Init Wiki template. Enjoy!')
            try:
                repo.remotes.origin.push()
                print(f'\t\t Success pushing wiki template into https://github.com/{r["REPO_ID"]}/wiki')
            except:
                print(f'\t\t Error pushing repo {r["REPO_ID"]}')
        else:
            print(
                f"\t\t Skipping repo wiki as it was created by user {commits[0].author} and has {len(commits)} commits")

