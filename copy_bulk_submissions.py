#!/usr/bin/env python3
"""Copy marking results into each submission's repository."""

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
    return parser.parse_args()


def main():
    args = parse_args()

    results_dir = args.results.resolve()
    submissions_dir = args.submissions.resolve()
    marking_rel = args.marking

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

    for result_folder in result_folders:
        submission_name = result_folder.name
        submission_dir = submissions_dir / submission_name

        if not submission_dir.is_dir():
            print(f"[SKIP] No matching submission folder for '{submission_name}'")
            skipped += 1
            continue

        dest = submission_dir / marking_rel

        if dest.exists():
            if not overwrite_all:
                print(f"[WARNING] {submission_name}: '{dest}' already exists.")
                answ = input("Overwrite this and ALL from now on? [y/N] ").strip().lower()
                if answ == "y":
                    overwrite_all = True
                else:
                    exit(1)
            print(f"[OVERWRITE] {submission_name}: removing existing '{dest}'")
            shutil.rmtree(dest)

        shutil.copytree(result_folder, dest)
        print(f"[OK] {submission_name}: copied '{result_folder}' -> '{dest}'")
        copied += 1

    print(f"\nDone: {copied} copied, {skipped} skipped.")


if __name__ == "__main__":
    main()
