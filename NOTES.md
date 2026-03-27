# Handling of repos

- [Handling of repos](#handling-of-repos)
  - [Using PyGithub](#using-pygithub)
  - [Using GitPyhon](#using-gitpyhon)
  - [Using git CLI](#using-git-cli)
    - [Tagging](#tagging)
  - [Using the REST API](#using-the-rest-api)
  - [Using `gh` CLI api tool](#using-gh-cli-api-tool)


## Using PyGithub

By using [github.GitCommit.GitCommit](https://pygithub.readthedocs.io/en/latest/github_objects/GitCommit.html#github.GitCommit.GitCommit) and [github.StatsContributor.StatsContributor](https://pygithub.readthedocs.io/en/latest/github_objects/StatsContributor.html#github.StatsContributor.StatsContributor).

Loading `util`:

```bash
$ python3
Python 3.6.9 (default, Jul 17 2020, 12:50:27)
[GCC 8.4.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> from github import Github, Repository, Organization, GithubException
>>> import util, utils_gh
>>> g = utils_gh.open_gitHub(token_file='/home/ssardina/gh-token-ssardina.txt')
/home/ssardina/gh-token-ssardina.txt
>>> repo = g.get_repo('RMIT-COSC1127-1125-AI/p2-multiagent-aione')
>>> for contrib in repo.get_stats_contributors():
...     print(contrib.author)
...
NamedUser(login="ssardina")
NamedUser(login="rockshan3906")
NamedUser(login="s123132")
>>> c = repo.get_commit('ecad94d73c5287a65981e299083561bf025a245e')
>>> print(c.author)
NamedUser(login="s12131")
>>> contribs = repo.get_stats_contributors()
>>> c = contribs[0]
>>> print(c.author)
NamedUser(login="ssardina")
>>> print(c.total)
1
```

Plain:

```shell
$ python

Type "help", "copyright", "credits" or "license" for more information.
>>> import github
>>> g = github.Github("sdlkajsdlakjsdklaasdasd")
>>> repo = g.get_repo("RMIT-COSC1127-1125-AI21/p0-warmup-danrowley24081979")
>>> print(repo.name)
p0-warmup-danrowley24081979
>>> print(repo.archived)
False
```


## Using GitPyhon

https://gitpython.readthedocs.io/en/stable/

```shell
```


## Using git CLI

### Tagging

```shell
$ git for-each-ref refs/tags/$TAG --shell --format='
TAG=%(refname)
TYPE=%(objecttype)
COMMIT=%(objectname)
TAGGER=%(tagger)
EMAIL=%(taggeremail)
DATE=%(taggerdate)
CONTENTS=%(contents)
'

TAG='refs/tags/submission'
TYPE='tag'
COMMIT='b4d4f4072d05cac814a527856b910396929ee475'
TAGGER='danrowley24081979 <64665857+msardina@users.noreply.github.com> 1627217610 +1000'
EMAIL='<64665857+msardina@users.noreply.github.com>'
DATE='Sun Jul 25 22:53:30 2021 +1000'
CONTENTS=''
``` 


```shell
$ git for-each-ref --shell --format="ref=%(refname:short) dt=%taggerdate:format:%s)" "refs/tags/*"

ref='submission' dt='1627217610 +1000'
```

```shell
$ git tag -l --format='%(refname)   %(taggerdate)'
```


## Using the REST API

See the [Getting Started](https://docs.github.com/en/rest/guides/getting-started-with-the-rest-api) guide.

Also see [this example](https://www.softwaretestinghelp.com/github-rest-api-tutori) commands.


Use `-u <username>:<token>` to access in authenticated mode. We store the token in variable `GHTOKEN`.


```shell
$ curl https://api.github.com/users/ssardina

# check user details
$ curl -i -u ssardina:$GHTOKEN https://api.github.com/user

# list all repos of an organization
$ curl -i -u ssardina:$GHTOKEN https://api.github.com/orgs/RMIT-COSC1127-1125-AI21/repos


# check a repo
$ curl -i -u ssardina:$GHTOKEN https://api.github.com/repos/RMIT-COSC1127-1125-AI21/p0-warmup-msardina

# inspect tags of a repo
$ curl -H "Accept: application/vnd.github.v3+json" -u ssardina:$GHTOKEN https://api.github.com/repos/RMIT-COSC1127-1125-AI21/p0-warmup-danrowley24081979/tags 


# Set plain protection rule
# https://docs.github.com/en/rest/reference/repos#update-branch-protection--parameters
 
$ curl \
  -u ssardina:$GHTOKEN -X PUT \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/RMIT-COSC1127-1125-AI21/p0-warmup-msardina/branches/master/protection \
  -d '{"required_status_checks": null, "enforce_admins": false, "required_pull_request_reviews": null, "allow_force_pushes" : false, "restrictions" : null }'

# Delete protection on branch
$ curl \
  -u ssardina:$GHTOKEN -X DELETE \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/RMIT-COSC1127-1125-AI21/p0-warmup-msardina/branches/master/protection 
```


To check all commis in branch `Dev`:

```
$ curl  -H "Accept: application/vnd.github+json"  \
  -H "Authorization: token $GHTOKEN" \
  https://api.github.com/repos/RMIT-COSC1127-1125-AI22/p2-pacmanmasters/commits\?sha=Dev
```

## Using `gh` CLI api tool

The `gh` command line tool makes accessing the GH API easier

- You can get the tool from: https://github.com/cli/cli 
- Manual: https://cli.github.com/manual/

First, you need to authenticate:

```shell
$ gh auth login --with-token < ~/.ssh/keys/gh-token-ssardina.txt
```

Then we can use the following to get all collaborators of a repo:

```shell
$ gh api -H "Accept: application/vnd.github+json" repos/RMIT-COSC1127-1125-AI22/p2-artificialidiot/collaborators
```


