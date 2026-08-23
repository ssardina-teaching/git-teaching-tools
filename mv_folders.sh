#!/bin/bash
#
# mv_folders.sh - Move a list of folders from one directory to another.
#
# For each name X listed in a text file (one name per line), this script
# moves the folder A/X to B/X.
#
# Usage:
#   ./mv_folders.sh <names_file> <folder_A> <folder_B>
#
#   names_file  Text file containing one folder name per line.
#   folder_A    Source directory containing the folders to move.
#   folder_B    Destination directory the folders will be moved into.
#
# Example:
#   ./mv_folders.sh names.txt . submissions/
#
# Blank lines in names_file are skipped. If a source folder A/X does not
# exist, a warning is printed and that entry is skipped.

usage() {
    echo "Usage: $0 <names_file> <folder_A> <folder_B>" >&2
    echo "  names_file  Text file with one folder name per line" >&2
    echo "  folder_A    Source directory containing the folders" >&2
    echo "  folder_B    Destination directory to move the folders into" >&2
}

if [[ $# -ne 3 ]]; then
    echo "Error: expected 3 arguments, got $#." >&2
    usage
    exit 1
fi

names_file="$1"
folder_a="$2"
folder_b="$3"

if [[ ! -f "$names_file" ]]; then
    echo "Error: names file '$names_file' not found." >&2
    usage
    exit 1
fi

if [[ ! -d "$folder_a" ]]; then
    echo "Error: source folder '$folder_a' does not exist." >&2
    usage
    exit 1
fi

if [[ ! -d "$folder_b" ]]; then
    echo "Error: destination folder '$folder_b' does not exist." >&2
    usage
    exit 1
fi

while IFS= read -r name; do
    # Skip empty lines
    [[ -z "$name" ]] && continue

    src="$folder_a/$name"
    dst="$folder_b/$name"

    if [[ ! -e "$src" ]]; then
        echo "Warning: '$src' not found, skipping." >&2
        continue
    fi

    echo "Moving $src -> $dst"
    mv -- "$src" "$dst"
done < "$names_file"
