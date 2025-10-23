# Teaching scripts

This repo contains useful scripts I developed over the years (since 2015!) to support student's submissions for homeworks and projects. They include tools to manage Git and  GitHub repositories, Google Workspaces (drive, spreadsheets), and shell/filesystem scripts.

They are almost all Python-based script, using two API libraries:

- [GitPython](https://gitpython.readthedocs.io/en/stable/index.html) (scripts `git_-_xxx.py`):  to perform GIT operations on the filesystem (e.g., cloning, commiting and pushing changes, reverting)
- [PyGitHub](https://github.com/PyGithub/PyGithub) (scripts `gh_xxx.py`): to perform API calls to [GitHub REST API](https://docs.github.com/en/rest?apiVersion=2022-11-28).
- Various libraries for accessing Google resorces (spreadsheets, Drive, etc.). These scripts are named `gg_xxx.py`

Feel free to use them as desired. No guarantees and I am sure they will have bugs or out-dated code! Open an issue or PR as needed.  😉

- [Teaching scripts](#teaching-scripts)
  - [Setup](#setup)
  - [GitHub Scripts](#github-scripts)
    - [Manual testing at development](#manual-testing-at-development)
    - [`gh_classroom_collect.py`: collect repos from a GH Organizations](#gh_classroom_collectpy-collect-repos-from-a-gh-organizations)
    - [`gh_authors_collect.py`: extract commits per author](#gh_authors_collectpy-extract-commits-per-author)
    - [`gh_create_wiki.py`: push Wiki template to list of repos](#gh_create_wikipy-push-wiki-template-to-list-of-repos)
    - [`gh_member_bulk_team.py`: add/delete GH username to GH teams](#gh_member_bulk_teampy-adddelete-gh-username-to-gh-teams)
    - [`gh_pr_merge.py`: bulk merge of PRs](#gh_pr_mergepy-bulk-merge-of-prs)
    - [`gh_pr_feedback_create.py`: create Feedback PRs](#gh_pr_feedback_createpy-create-feedback-prs)
    - [`gh_pr_check_merged_forced.py`: check for merged PR and forced pushes](#gh_pr_check_merged_forcedpy-check-for-merged-pr-and-forced-pushes)
    - [`gh_pr_post_result.py`: push comments to repo's PRs](#gh_pr_post_resultpy-push-comments-to-repos-prs)
    - [`gh_pr_post_comment.py`: push a message to PRs](#gh_pr_post_commentpy-push-a-message-to-prs)
    - [`gh_workflow.py`: run automarking workflow](#gh_workflowpy-run-automarking-workflow)
    - [`gh_commit_after.py`: get commits after a date](#gh_commit_afterpy-get-commits-after-a-date)
    - [`gh_tag_after.py`: get repos with a given task after a date](#gh_tag_afterpy-get-repos-with-a-given-task-after-a-date)
    - [`ghc_build_reporter.py`: build YAML classroom reporter](#ghc_build_reporterpy-build-yaml-classroom-reporter)
    - [`gh_user_access.py`: get repos and accesses of org](#gh_user_accesspy-get-repos-and-accesses-of-org)
    - [`gh_issue_labels.py`: get/update issue labels in a GH repo](#gh_issue_labelspy-getupdate-issue-labels-in-a-gh-repo)
    - [`gh_refresh_invite.sh`: Refresh pending repo invitations](#gh_refresh_invitesh-refresh-pending-repo-invitations)
  - [Git Tools](#git-tools)
    - [`git_clone_submissions.py`: batch git cloning](#git_clone_submissionspy-batch-git-cloning)
    - [`git_batch_commit.sh`: bulk commit and push to repos](#git_batch_commitsh-bulk-commit-and-push-to-repos)
    - [`git_revert.py`: revert commits done late](#git_revertpy-revert-commits-done-late)
  - [Google Scripts](#google-scripts)
    - [`gg_get_worksheet.py`: download Google Sheet worksheet as CSV file](#gg_get_worksheetpy-download-google-sheet-worksheet-as-csv-file)
    - [`gg_sheet_submissions.py`: download submissions from Google Sheets](#gg_sheet_submissionspy-download-submissions-from-google-sheets)
    - [`gg_drive_download.py`: download files in Drive folder](#gg_drive_downloadpy-download-files-in-drive-folder)
  - [Useful shell commands](#useful-shell-commands)
  - [Contributors](#contributors)

## Setup

To install all requirements run this in your Python virtual environment:

```bash
$ pip install -r requirements.txt
```

The libraries used are:

- GitHub REST documentation: <https://docs.github.com/en/rest>
- PyGithub: <https://github.com/PyGithub/PyGithub>
- gitpython: <http://www.legendu.net/misc/blog/hands-on-GitPython/>
- gh API CLI tool: <https://github.com/cli/cli> ([manual](https://cli.github.com/manual/))

## GitHub Scripts

These `gh_xxx.py` scripts mostly use [PyGithub](https://github.com/PyGithub/PyGithub). Scripts will require a GitHub access token that allows access the corresponding repos/organization.

Another tool that one can consider is [gh API CLI](https://github.com/cli/cli) tool; see the [manual](https://cli.github.com/manual/).

### Manual testing at development

We can run interactively first at development time; for example:

```shell
>>> import util
>>> g = util.open_gitHub(token_file="/home/ssardina/.ssh/keys/gh-token-ssardina.txt")
>>> repo = g.get_repo("RMIT-COSC2780-2973-IDM25/workshop-5-ssardina")
>>> ws = repo.get_workflows()
>>> ws[0].create_dispatch(ref="main")
```

### `gh_classroom_collect.py`: collect repos from a GH Organizations

Produces a CSV file with all the repos in a given GitHub Classroom for a particular assignment, using its corresponding prefix.

For example, to get all the repos submitted for AI24 project with prefix `p3-prolog` into a CSV file `repos.csv`:

```shell
python ./gh_classroom_collect.py -t ~/.ssh/keys/gh-token-ssardina.txt RMIT-COSC1127-1125-AI24  p3-prolog repos.csv |& tee -a repos.log
```

> [!NOTE]
> The CSV `repo.csv` file will be used for many later tasks, including cloning the repos locally using script `git_clone_submissions.py`, extracting collaborators, etc.

### `gh_authors_collect.py`: extract commits per author

Produce a CSV file with how many commits each author has done per repo. For example:

```shell
$ python ./gh_authors_collect.py -t ~/.ssh/keys/github-token-ssardina.txt
    --tag submission -- repos.csv authors.csv
```

The `--tag` option restricts to tags finishing in a given tag. If no tag is given, the whole repo is parsed to the head of `main`.

### `gh_create_wiki.py`: push Wiki template to list of repos

This script will push a template Wiki to each repo:

```bash
python ./gh_create_wiki.py repos.csv ./wiki-template
```

See [wiki-template](wiki-template/) for an example of a Wiki template.

### `gh_member_bulk_team.py`: add/delete GH username to GH teams

This script will add a GH username to GH teams in an organization. For example, to add Axel to all the teams except teams `teachers` and `headtutor`:

```shell
$ python gh_member_bulk_team.py RMIT-COSC2780-2973-IDM24  axelahmer  --nteams  "teachers" "headtutor"
Running the script on: 2024-05-18-00-35-27
Sat, 18 May 2024 00:35:27 INFO     Getting organization RMIT-COSC2780-2973-IDM24...
Sat, 18 May 2024 00:35:27 INFO     Getting GH user for axelahmer...
Teams available: ['AI NPCs', 'ASP Dads', 'Galacticos', 'gASP', 'Harry Ron and Hermoine', 'IDM Project', 'Intellect Realm', 'Inter-Dimensional Masochists (IDM)', 'Logic Nexus', 'Lorem Ipsum', 'Mister World Wide', 'Prolog nightmares again', 'sajeevan', 'Super awesome team name', 'teachers', 'TRY']
Adding user **axelahmer** to team AI NPCs
Adding user **axelahmer** to team ASP Dads
Adding user **axelahmer** to team Galacticos
Adding user **axelahmer** to team gASP
Adding user **axelahmer** to team Harry Ron and Hermoine
Adding user **axelahmer** to team IDM Project
Adding user **axelahmer** to team Intellect Realm
Adding user **axelahmer** to team Inter-Dimensional Masochists (IDM)
Adding user **axelahmer** to team Logic Nexus
Adding user **axelahmer** to team Lorem Ipsum
Adding user **axelahmer** to team Mister World Wide
Adding user **axelahmer** to team Prolog nightmares again
Adding user **axelahmer** to team sajeevan
Adding user **axelahmer** to team Super awesome team name
Adding user **axelahmer** to team TRY
```

### `gh_pr_merge.py`: bulk merge of PRs

This script can be used to merge PRs in a set of repos. This is useful when a PR have been opened in each student repo to implement updates in the project spec via GitHub Classroom sync feature (new in 2024).

For example, to merge PR with title `Sync` from the 40th repo in `repo.csv`:

```shell
python ./gh_pr_merge.py repos.csv -t ~/.ssh/keys/gh-token-ssardina.txt --title Sync --start 40 |& tee -a merge_pr.log
```

### `gh_pr_feedback_create.py`: create Feedback PRs

Check which repos are missing an expected Feedback PR #1 from GitHub Classroom; and create them as needed. This may be needed because sometimes GH Classroom failed to create the PRs in some repos.

For example:

```shell
python ./gh_pr_create.py -t ~/.ssh/keys/gh-token-ssardina.txt repos.csv a7b3d7aee55d00d55ee29b8a505d17fc8283e9f8 |& tee pr_create.log
```

Notice that the script needs the list of repos to consider ()`repos.csv`) and the base sha to create the Feedback branch and corresponding PR. Because the repos were created by GH Classroom, the first commit should have the same sha than the original staff template.

### `gh_pr_check_merged_forced.py`: check for merged PR and forced pushes

This script will check for PRs that have been merged and

```shell
python ../git-hw-submissions.git/gh_pr_check_merged_forced.py  -t ~/.ssh/keys/gh-token-ssardina.txt   repos.csv
```

It will leave two CSV files `pr_merged.csv` and `pr_forced.csv` with the corresponding repos' ids.

### `gh_pr_post_result.py`: push comments to repo's PRs

This tool will push comments (e.g., homework feedback and results) to PRs in GH repositories. This may be useful to provide feedback and results to students after automarking. It requires:

- A CSV file with the list of all relevant repos to process (e.g., student's projects).
- A CSV file with the marking results (points, marks, comments, etc).
- A folder with the automarking reports as text files.
- A Python file defining two functions that process a row in the marking results:
  - `check_submission`: can be used to check if the row contains a legal/successful submission. It will return whether the row/submission needs to be skipped and a string message to be posted to the PR, if any (e.g., the reason why the submission was not marked and skipped).
  - `report_feedback`: produce the actual feedback text to be posted in the PR.
  - `FEEDBACK_MESSAGE`: message to post after a report.
  - `get_repo()` [OPTIONAL]: returns a list of repos to process.

Now push all feedback to their pull requests from fist row (1) to row 5:

```shell
python ./gh_pr_post_result.py repos.csv marking.csv feedback_p2.py reports  -t ~/.ssh/keys/gh-token-ssardina.txt
```

It is best to use `--dry-run` first to test it.

Check repor builder examples:

- `gh_pr_post_result_example_marking.py`: build a full message for an assignment result.
- `gh_pr_post_result_example_message.py`: simple message to post to some repos.

### `gh_pr_post_comment.py`: push a message to PRs

```shell
python ../tools/git-hw-submissions.git/gh_pr_post_comment.py -t ~/.ssh/keys/gh-token-ssardina.txt repos.csv message_pr.py
```

File `message_pr.py` defines constant `MESSAGE` with placement `ghu` fr GH username, and function `get_repo()` which is a list of the relevant repo to posts (`None` if all).

### `gh_workflow.py`: run automarking workflow

This script can do several operations on workflows:

1. Start a run of a workflow (create a dispatch) in the repository of students. This is usually an automarking workflow that is connected and reports to GitHub Classroom.
    - In this way, we can decide when the workflow should run, rather than in each push (which will consume all the budget quickly!)
2. Extract the URL to the HTML page of a job for a run of a workshop. This URL would be the automarker report in the repo (showing the automarking process and table of results).
    - Note this URL is still accessible even if the actions are disabled.
3. Delete workflow runs.

Examples:

```shell
# start dispatching workflows with name "Autograding" on the last commit before a date
$ python ../../tools/git-hw-submissions.git/gh_workflow.py -t ~/.ssh/keys/gh-token-ssardina.txt --name Autograding --until 2025-04-08T12:00 --run-name "Automarking up April 8 12pm" -- start repos.csv |& tee -a autograde-2025-04-08T1200.log

# get all the HTML URL to workflow job reports
$ python ../../tools/git-hw-submissions.git/gh_workflow.py -t ~/.ssh/keys/gh-token-ssardina.txt --name Autograding --run-name "Autograding Test" -repos baoly19,anurag060197,minhphamhuy -- jobs repos.csv

# delete all worflow runs after April 8, 2025 - 12pm
$ python gh_workflow.py -t ~/.ssh/keys/gh-token-ssardina.txt --name Autograding --until 2025-04-08T12:00 --repos ssardina -- delete repos.csv
```

### `gh_commit_after.py`: get commits after a date

To get the commits after a date (and the one just before):

```shell
python ../../tools/git-hw-submissions.git/gh_commits_after.py -t /home/ssardina/.ssh/keys/gh-token-ssardina.txt  --ignore ssardina --since 2025-04-08T12:00 --repos minhphamhuy ssardina DeltaEchoVictor101  -- repos.csv
```

This was used to revert back to a previous commit before a deadline when the student has (illegally) push more changes after a deadline.

### `gh_tag_after.py`: get repos with a given task after a date

To get the repos that have tag commit after a given date:

```shell
$ python ./tools/git-teaching-tools.git/gh_tags_after.py repos.csv submission -t ~/.ssh/keys/gh-token-ssardina.txt --since 2025-10-15T23:00

$ cat tags-repos-2025-10-23_21-35.csv
REPO_ID_SUFFIX,TAG,COMMIT,DATE
lanadavies,submission,5dbac2b,2025-10-19T21:30:33+11:00
longcent,submission,5cd116c,2025-10-17T22:57:16+11:00
pugdev17,submission,b0568af,2025-10-15T23:53:25+11:00
rishabh-despacito,submission,0451595,2025-10-16T14:50:11+11:00
```

The we can just clone those ones in a special folder (e.g., late submissions after main marking has been done).

### `ghc_build_reporter.py`: build YAML classroom reporter

Builds the section for the [classroom-resources/autograding-grading-reporter@v1](https://github.com/classroom-resources/autograding-grading-reporter) runner from the definition of the tests. It is too cumbersome to do it manually! 😉

```yaml
    - name: Autograding Reporter
      uses: classroom-resources/autograding-grading-reporter@v1
      env:
        LIVE_RESULTS: "${{steps.live.outputs.result}}"
        MESSI_RESULTS: "${{steps.messi.outputs.result}}"
        MAP-SOUND_RESULTS: "${{steps.map-sound.outputs.result}}"
        MAP-OPTIMAL_RESULTS: "${{steps.map-optimal.outputs.result}}"
      with:
        runners: live,messi,map-sound,map-optimal
```

Also reports the total marks in the automarking.

An example of a run:

```shell
$ python ../../tools/git-hw-submissions.git/ghc_build_reporter.py workshop-4-ssardina.git/.github/workflows/classroom.yml
Total marks:  100                                                                                                     │* 2732b6e - (HEAD -> main, origin/main, origin/HEAD) Much better automarking; run-name and sha inputs (18 hours ago) <
                                                                                                                      │ssardina>
- name: Autograding Reporter                                                                                          │* 7f89ba2 - solving diet puzzle (4 days ago) <Dev Bakshi>
  uses: classroom-resources/autograding-grading-reporter@v1                                                           │* 77e99c8 - implementing class scheduling (4 days ago) <Dev Bakshi>
  env:                                                                                                                │* fa68569 - using set for predicates (4 days ago) <Dev Bakshi>
        SHOP_4_RESULTS: ${{steps.shop_4.outputs.result}}                                                              │* 1c283a1 - adding shop for iten predicate (4 days ago) <Dev Bakshi>
        SHOPS_FOR_ITEM_2_RESULTS: ${{steps.shops_for_item_2.outputs.result}}                                          │* b81a363 - add deadline (3 weeks ago) <github-classroom[bot]>
        SHOPS_FOR_ITEMS_2_RESULTS: ${{steps.shops_for_items_2.outputs.result}}                                        │* 726a5f8 - Setting up GitHub Classroom Feedback (3 weeks ago) <github-classroom[bot]>
        INTERSECTION_3_RESULTS: ${{steps.intersection_3.outputs.result}}                                              │* 4ec8cc2 - (origin/feedback) GitHub Classroom Feedback (3 weeks ago) <github-classroom[bot]>
        DIFF_3_RESULTS: ${{steps.diff_3.outputs.result}}                                                              │* 1c26843 - Initial release IDM25 (3 weeks ago) <ssardina>
        UNION_3_RESULTS: ${{steps.union_3.outputs.result}}                                                            │❯ gitlog
        WHERE-LIVE_RESULTS: ${{steps.where-live.outputs.result}}                                                      │* b98e5ff - (HEAD -> main, origin/main, origin/HEAD) Revert "adding shop for iten predicate" (6 seconds ago) <ssardina
        MAP_COLORING_RESULTS: ${{steps.map_coloring.outputs.result}}                                                  │>
        CLASS_SCHEDULING_RESULTS: ${{steps.class_scheduling.outputs.result}}                                          │* 2732b6e - Much better automarking; run-name and sha inputs (19 hours ago) <ssardina>
        DIET_RESULTS: ${{steps.diet.outputs.result}}                                                                  │* 7f89ba2 - solving diet puzzle (4 days ago) <Dev Bakshi>
        DIET-Q1_RESULTS: ${{steps.diet-q1.outputs.result}}                                                            │* 77e99c8 - implementing class scheduling (4 days ago) <Dev Bakshi>
        DIET-Q2_RESULTS: ${{steps.diet-q2.outputs.result}}                                                            │* fa68569 - using set for predicates (4 days ago) <Dev Bakshi>
        DIET-Q3_RESULTS: ${{steps.diet-q3.outputs.result}}                                                            │* 1c283a1 - adding shop for iten predicate (4 days ago) <Dev Bakshi>
  with:                                                                                                               │* b81a363 - add deadline (3 weeks ago) <github-classroom[bot]>
    runners: shop_4,shops_for_item_2,shops_for_items_2,intersection_3,diff_3,union_3,where-live,map_coloring,class_sch│* 726a5f8 - Setting up GitHub Classroom Feedback (3 weeks ago) <github-classroom[bot]>
eduling,diet,diet-q1,diet-q2,diet-q3
```

Then one can copy and paste this in the `classroom.yaml` workflow file.

### `gh_user_access.py`: get repos and accesses of org

This script allows to get all repos in an organization and its contributors with their acceses (read/write/admin).

```shell
python ../tools/git-hw-submissions.git/gh_user_access.py -t ~/.ssh/keys/gh-token-ssardina.txt list RMIT-COSC2780-2973-IDM25 ssardina -s 1 -e 10 |& tee -a 2025.04.13.repo-org.log
```

This could be good to later inspect and handle users  who have dropped the course (may want to remove their access to the repos).

### `gh_issue_labels.py`: get/update issue labels in a GH repo

This script allows to get the current list of issue labels from a repo, as a JSON file, or push a given list of labels, including replacing the labels completely.

```shell
# get the current list of labels into labels.json
$ python gh_issue_labels.py get harry-honours-2025/honours-software -t jasdlakjsdlj1223d --file labels.json

# push completely the set of labels
$ python gh_issue_labels.py push harry-honours-2025/honours-software -tf  ~/.ssh/keys/gh-token-ssardina.txt --file labels.json --replace
```

### `gh_refresh_invite.sh`: Refresh pending repo invitations

When using GitHub Classroom, seems some students get the repo created but have no access and their invites do not work. They are still showing as "pending invitation". There is an discssion on this [here](https://github.com/orgs/community/discussions/72283). It seems the problem is that GitHub Classroom invitations expire _before_ students can accept them 😕. While we all hope GitHub resolves this soon, I built a temporary workaround that has already helped our students regain access quickly.

The suggestion is to refresh the invitation: delete and re-invite. Doing it manual (for many students) become time consuming, so the script `gh_refresh_invite.sh` allows to quickly do the refresh.

The script is a bash script and requires install and authettication of [GitHub CLI](https://github.com/cli/cli?tab=readme-ov-file). Then you can run:

```shell
$ refresh_invite.sh RMIT-COSC1127-3117-AI25 p2-prolog-garimlaw
Processing invitation for user: garimlaw
  -> Deleting invitation ID 291199199 from RMIT-COSC1127-3117-AI25/p2-prolog-garimlaw...
  -> Re-creating invitation for user: garimlaw
```


## Git Tools

These tools use [GitPython](https://gitpython.readthedocs.io/en/stable/tutorial.html) module to have Git API in Python.

We can run interactively first at development time; for example:

```shell
>>> import util
>>> g = util.open_gitHub(token_file="/home/ssardina/.ssh/keys/gh-token-ssardina.txt")
>>> repo = g.get_repo("RMIT-COSC2780-2973-IDM25/workshop-5-ssardina")
>>> ws = repo.get_workflows()
>>> ws[0].create_dispatch(ref="main")
```

### `git_clone_submissions.py`: batch git cloning

This tool clones a set of student/team repositories listed in a CSV file at a given _tagged_ commit. The CVS file should contain the team name (under column name `TEAM`) and a GIT ssh link (under column name `GIT-URL`).

If a repository already exists, it will be _updated_ automatically:

- if the tag changed to a different commit, the new commit will be pulled;
- if the repo does not have the tag anymore (the student has withdraw the submission), the local copy will be removed from disk.

At the end, the script produces a CSV file with the information of each repo successfully cloned, including commit id (`commit`), time of the commit (`submitted_at`), and time of the tagging (`tagged_at`).

For example, to clone Project 0 at commit with tag "`final`" using the database of repos `repos.csv`:

```shell
python ./git_clone_submissions.py --file-timestamps timestamps.csv repos.csv final submissions/ &| tee clone.log
```

All repos will be cloned within folder `submissions/` and the file `timestamps.csv` will contain the timestamps and commits of each repo cloned successfully. The file will contain the date of the commit linked to the tag. If the tag is an annotated tag (and not just lightweight tag), it will also include the date tagged (otherwise they will be assumed the same); see [annotated vs lightweight tags](https://git-scm.com/book/en/v2/Git-Basics-Tagging).

To just clone the last commit in the master branch, use `main` as the tag.

The timezone used is defined by constant `TIMEZONE` in the script (defaults to `Australia/Melbourne` time zone).

### `git_batch_commit.sh`: bulk commit and push to repos

This script allows to commit and push changes to a collection of repos that already exist in a folder. This is useful to make edits to students' repos after they have been created.

### `git_revert.py`: revert commits done late

Sometime we want to revert back to some previous commit, for example, if the student has done late work which has already been autograder by the workflow.

```shell
python ../../tools/git-hw-submissions.git/git_revert.py submissions/deltaechovictor101/ b81a363 --keep .github
```

>[!NOTE]
> Generally you get the commit to go back by getting the last commit until a certain date (deadline). You can use script [`gh_commits_after.py`](#gh_commit_afterpy-get-commits-after-a-date) to get that for a collection of repos.

## Google Scripts

To access [Google Workspaces](https://developers.google.com/workspace) resources via the Google API, one needs to enable the API access and get a proper authentication credentials. Different APIs are provided for teh different resources (drive, gmail, sheet, etc.).

For authentication to Google Workspaces one needs the the application configurations file from APIs Console. Check the [Google Sheet API setup process](https://developers.google.com/sheets/api/quickstart/python) to obtain a `client_secret.json` (same as `credentials.json`) file for your project. PyDrive2 also explains how to get the file [here](https://docs.iterative.ai/PyDrive2/quickstart/#authentication).

All access to Google API requires authentication; usually the workflow is as follows:

- Go to the [Google API Access Panel](https://console.developers.google.com/apis/credentials).
- Create a project.
- Create an OAuth consent screen.
- Create credentials of type "OAuth Client ID".
- Download the JSON file of such credentials and name it `client_secrets.json`
- Place the file in the same directory as the scripts.

> [!TIP]
> Read [Integrating Google Drive API with Python: A Step-by-Step Guide](https://medium.com/the-team-of-future-learning/integrating-google-drive-api-with-python-a-step-by-step-guide-7811fcd16c44).
>
> - [Google Sheet API](https://developers.google.com/sheets/api/guides/concepts) access:
>   - [gsheets](https://gsheets.readthedocs.io/en/stable/index.html)
>   - [pygsheets](https://github.com/nithinmurali/pygsheets)
> - [Google Drive API](https://developers.google.com/drive/api/guides/about-sdk) access:
>   - [PyDrive2](https://docs.iterative.ai/PyDrive2/) package for more abstract access to the .
> - [Google Forms API](https://developers.google.com/forms/api/guides):

### `gg_get_worksheet.py`: download Google Sheet worksheet as CSV file

This script allows to download a Google Sheet from the cloud. It relies on the [gsheets](https://gsheets.readthedocs.io/en/stable/index.html) package to access the [Google Sheet API](https://developers.google.com/sheets/api/guides/concepts).

The sheet to download is often a marking sheet. For example, to get the sheet `MARKING` from Google Spreadsheet with id `1kX-fa3_DMNDQROUr1Y-cG89UksTUUqlYdrNcV1yN6NA`:

```shell
python ./gg_get_worksheet.py 1kX-fa3_DMNDQROUr1Y-cG89UksTUUqlYdrNcV1yN6NA MARKING -c ~/.ssh/keys/credentials.json -o marking.csv
```

The `credentials.json` was obtained via the [Google Sheet API setup process](https://developers.google.com/sheets/api/quickstart/python). The first time that is used, a permission will be required. A certificate file `storage.json` will be left then that will allow direct access from there on (until certificate expires).

The authentication will be done via console. Use `--webserver` to open an actual browser.

### `gg_sheet_submissions.py`: download submissions from Google Sheets

This script can process Google Sheets produced by Google Forms, and download links to uploaded files in each submission. Files will be placed in folders identifying each submission, for example with the student number or email associated to the submission.

For example, to download the files recorded in column `G` in the worksheet `W4-resolution` of a Google Sheet with id `1ogCRbx...`, and save each in a folder `submission/XXXX` where `XXXX` is the student number recorded in column `C`:

```shell
python ./gg_sheet_submissions.py 1ogCRbxB3seVhoqhD7iBmVZ8EdpvGEB94oLowDIs5s2g W4-resolution tea --output test/submissions --file-name test.cnf --column-id C --column-file G
```

### `gg_drive_download.py`: download files in Drive folder

This tool allows downloading file submissions in a Google Drive folder, usually submitted via a Google Form by students. It uses [PyDrive2](https://docs.iterative.ai/PyDrive2/) package for more abstract access to the [Google Drive API](https://developers.google.com/drive/api/guides/about-sdk).

```shell
python ./gg_drive_download.py 1mttf61NwuFNY25idwWw5AKzV3tQQbwlMp980i-9vnkK3PIV4o7ZOtykWvjM-VLqmHuYJ0jX4 -c ~/.ssh/keys/credentials.json --output test/submissions --file-name submissions.cnf
```

This script is a new and simpler version of the one in [this repo](https://github.com/ssardina-teaching/google-assignment-submission).

## Useful shell commands

Once all git repos have been cloned in `git-submissions/`, one can build zip files from the submissions into directory `zip-submissions/` as follows:

```bash
for d in git-submissions-p2/*; do echo "============> Processing ${d}" ; zip -q -j "./zip-submissions-p2/`basename "$d.zip"`" "${d}"/p2-multiagent/* ;done
```

or for the final CTF project:

```bash
for d in git-submissions-p4/*; do echo "============> Processing ${d}" ; zip -q -j "./zip-submissions-p4/`basename "$d.zip"`" "${d}"/pacman-contest/* ;done
```

To count the number of commits between dates:

```bash
git log --after="2018-03-26T00:00:00+11:00" --before="2018-03-28T00:00:00+11:00" | grep "Date:" | wc -l
```

To copy just the new zip files:

```bash
rsync  -avt --ignore-existing  zip-submissions-p4/*.zip AI18-assessments/project-4/zip-submissions/
```

## Contributors

- Prof. Sebastian Sardina (<ssardina@gmail.com>)
- Andrew Chester (head tutor in AI - 2020-2024)
- Jonathon Belotti (helped in AI-2018)
