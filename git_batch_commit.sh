#!/bin/bash

TEMPLATE=project-examalloc-template.git


##### GET OPTIONS FROM COMMAND-LINE
NO_ARGS=$#   # Get the number of arguments passed in the command lin
ME=`basename "$0"`
DRY_RUN=false

if [ "$NO_ARGS" -lt 1 ]; then
  echo -e "USAGE: ./$ME <folder with repos> [--dry-run]" 
  exit
fi

# Parse arguments
for arg in "$@"; do
  case "$arg" in
    --dry-run)
      DRY_RUN=true
      ;;
  esac
done

echo
echo "# arguments called with ---->  ${@}     "
echo "# \$1 ---------------------->  $1       "
echo "# \$2 ---------------------->  $2       "
echo "# \$3 ---------------------->  $3       "
echo "# path to me --------------->  ${0}     "
echo "# parent path -------------->  ${0%/*}  "
echo "# my name ------------------>  ${0##*/} "
echo

# change file separator to handle filename with spaces
# https://www.cyberciti.biz/tips/handling-filenames-with-spaces-in-bash.html
SAVEIFS=$IFS
IFS=$(echo -en "\n\b")

#########################
# HERE GOES THE SCRIPT
#########################

run() {
  if $DRY_RUN; then
    echo "[DRY-RUN] "$*""
  else
    "$@"
  fi
}


COUNTER=0
for dir in $(ls -d $1/*) ; do

    # continue if not a directory
  	[ ! -d "$dir" ] && continue

    let COUNTER++
    echo "=================> Processing folder $COUNTER: "$dir""
    URL=$(git -C "$dir" remote show origin | grep Fetch.URL | sed 's/.*git@\(.*\):/http:\/\/\1\//')
    echo "REPO: $URL"
    run git -C "$dir" pull  # first update repo

    ######################################################
    # HERE IS WHERE WE DO THE CHANGES TO THE REPO IN $d/
    ######################################################
    # Get into student repo, add, commit and push

    # sync files from template
    SYNC_FILES=( 
      $TEMPLATE/./README.md 
      # $TEMPLATE/./EXAM_ALLOCATE.md 
      # $TEMPLATE/./LICENSE 
      $TEMPLATE/./benchmarks/README.md 
      $TEMPLATE/./examalloc/validator/README.md 
      # $TEMPLATE/./pyproject.toml
    )
    run rsync -av --delete --relative "${SYNC_FILES[@]}" $dir/

    # run rm $dir/RURBICS.md

    MESSAGE="Update docs and spec."
    MESSAGE="Update project TOML file."
    MESSAGE="Clarification on capitalisation of IDs and timeslots coincidences."
    MESSAGE="Updates on doc; clarify constraints; fix URL link to FAQ."
    MESSAGE="Explicit note on timeslot coincidence for 2+ groups."
    MESSAGE="Further clarified level 1 constraints"
    MESSAGE="Updated submission links and report folder"


    ######################################################
    # FINISH CHANGES
    ######################################################

    echo "Will commit with message: **$MESSAGE**"
    run git -C $dir add .
    run git -C $dir commit -m $MESSAGE
    run git -C $dir push

    # Wait a bit to not be pushed out....
    sleep 3
    echo next...
done

# restore $IFS
IFS=$SAVEIFS



