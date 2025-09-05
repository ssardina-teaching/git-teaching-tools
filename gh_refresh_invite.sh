#!/bin/bash
#
# Reinvites all pending invitations for a given GitHub repository
#
# Taken from https://github.com/orgs/community/discussions/72283#discussioncomment-14270110
#
#   $ ./gh_refresh_invite.sh RMIT-COSC1127-3117-AI25 p2-prolog-s3952879
#   Processing invitation for user: s3952879
#     -> Deleting invitation ID 291175054 from RMIT-COSC1127-3117-AI25/p2-prolog-s3952879...
#     -> Re-creating invitation for user: s3952879
#   

##### GET OPTIONS FROM COMMAND-LINE
NO_ARGS=$#   # Get the number of arguments passed in the command line

MY_NAME=${0##*/} 

#echo
#echo "# arguments called with ---->  ${@}     "
#echo "# \$1 ---------------------->  $1       "
#echo "# \$2 ---------------------->  $2       "
#echo "# path to me --------------->  ${0}     "
#echo "# parent path -------------->  ${0%/*}  "
#echo "# my name ------------------>  ${0##*/} "
#echo
#exit

if [ "$NO_ARGS" != 2 ]; then
    printf "**** Script by Sebastian Sardina (2025) \n\n"
    printf "usage: ./$MY_NAME <gh_org> <repo_id>\n"
    exit
else
    # Ensure an organization name is provided
    org_name=$1
    repo_name="$org_name/$2"

    # Check that $1 starts with "<FORMAT>"
    # if [[ ! "$1" =~ ^<FORMAT>* ]]; then
    #     echo "Error: Repository name must match format '<FORMAT>'"
    #     exit 1
    # fi


    # Get pending invitations for this repo
    invites=$(gh api "repos/$repo_name/invitations" --jq '.[] | "\(.id),\(.invitee.login)"' 2>/dev/null)

    # Delete the invite
    if [ -n "$invites" ]; then
        echo "$invites" | while IFS=',' read invite_id invitee; do
            echo "Processing invitation for user: $invitee"
            echo "  -> Deleting invitation ID $invite_id from $repo_name..."
            gh api "repos/$repo_name/invitations/$invite_id" -X DELETE --silent
            echo "  -> Re-creating invitation for user: $invitee"
            gh api "repos/$repo_name/collaborators/$invitee" -X PUT -f permission=write --silent
        done
    else
        echo "No invites found for this repository."
    fi
fi
