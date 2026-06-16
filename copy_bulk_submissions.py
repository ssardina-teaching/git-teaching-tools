#!/usr/bin/env python3
"""Copy marking results into each submission's repository.

e.g.:

    $ python copy_bulk_submissions.py asp-automarker.git/results/idm26/01-slots-f1 submissions marking --preserve

    or

    $ python copy_bulk_submissions.py asp-automarker.git/results/idm26/01-slots-f1 submissions marking/test-01
"""

import argparse
import shutil
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Copy result folders into each submission's repository under a marking subfolder."
    )
    parser.add_argument(
        "results",
        type=Path,
        help="Folder containing one result subfolder per submission (each is a git repo).",
    )
    parser.add_argument(
        "submissions",
        type=Path,
        help="Folder containing one subfolder per submission.",
    )
    parser.add_argument(
        "marking",
        help="Relative folder name inside each submission repo where results will be copied.",
    )
    parser.add_argument(
        "-p", "--preserve",
        action="store_true",
        help="Preserve basename of the result folder.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    results_dir = args.results.resolve()
    submissions_dir = args.submissions.resolve()
    dest_folder = Path(args.marking)
    if args.preserve:
        dest_folder = dest_folder / results_dir.name

    if not results_dir.is_dir():
        raise SystemExit(f"Results directory not found: {results_dir}")
    if not submissions_dir.is_dir():
        raise SystemExit(f"Submissions directory not found: {submissions_dir}")

    result_folders = sorted(p for p in results_dir.iterdir() if p.is_dir())
    if not result_folders:
        print("No result folders found. Nothing to do.")
        return

    copied = 0
    skipped = 0
    overwrite_all = False
    skip_all = False

    for result_folder in result_folders:
        submission_name = result_folder.name
        submission_dir = submissions_dir / submission_name

        if not submission_dir.is_dir():
            print(f"[SKIP] No matching submission folder for '{submission_name}'")
            skipped += 1
            continue

        dest = submission_dir / dest_folder

        if dest.exists():
            if skip_all:
                print(f"[SKIP] {submission_name}: '{dest}' already exists (skipping all).")
                continue
            if not overwrite_all:
                print(f"[WARNING] {submission_name}: '{dest}' already exists.")
                answ = input("Overwrite or skip this and ALL existing from now on? [y/s] ").strip().lower()
                if answ == "y":
                    overwrite_all = True
                elif answ == "s":
                    skip_all = True
                    continue
                else:
                    exit(1)
            print(f"[OVERWRITE] {submission_name}: removing existing '{dest}'")
            shutil.rmtree(dest)

        print(f"[OK] {submission_name}: copied '{result_folder}' -> '{dest}'")
        shutil.copytree(result_folder, dest)
        copied += 1

    print(f"\nDone: {copied} copied, {skipped} skipped.")


if __name__ == "__main__":
    main()
