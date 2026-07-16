import os
import re
import sys
from github import Github, GithubException


def get_job_annotations_pygithub(job_url, token=None):
    """Extracts annotations from a GitHub workflow job URL using PyGithub."""
    # Pattern to extract owner, repo, run_id, and job_id from the URL
    pattern = r"github\.com/([^/]+)/([^/]+)/actions/runs/(\d+)/job/(\d+)"
    match = re.search(pattern, job_url)

    if not match:
        raise ValueError("Invalid GitHub Job URL format.")

    owner, repo_name, run_id, job_id = match.groups()
    repo_full_name = f"{owner}/{repo_name}"

    # Initialize PyGithub client (Authenticated or Anonymous)
    # Note: Tokens are highly recommended to avoid strict rate limits
    g = Github(token) if token else Github()

    try:
        print(f"Connecting to repository: {repo_full_name}...")
        repo = g.get_repo(repo_full_name)

        print(f"Fetching workflow run ID: {run_id}...")
        # PyGithub has no direct get_workflow_job(); fetch the run and find the
        # matching job in its job list instead.
        run = repo.get_workflow_run(int(run_id))

        print(f"Fetching workflow job ID: {job_id}...")
        job = next((j for j in run.jobs() if j.id == int(job_id)), None)
        if job is None:
            print(f"Job ID {job_id} not found in run {run_id}.", file=sys.stderr)
            return None

        # The job object contains the check_run_url. We extract the check_run_id from it.
        # Format usually: https://api.github.com/repos/{owner}/{repo}/check-runs/{check_run_id}
        if not job.check_run_url:
            print("No check run associated with this job.", file=sys.stderr)
            return []

        check_run_id = int(job.check_run_url.split("/")[-1])
        print(f"Found Check Run ID: {check_run_id}. Fetching annotations...")

        # Get the check run object and retrieve its annotations
        check_run = repo.get_check_run(check_run_id)
        annotations = check_run.get_annotations()

        # Convert the PaginatedList of CheckRunAnnotation objects to a standard list
        return list(annotations)

    except GithubException as e:
        print(f"GitHub API Error ({e.status}): {e.data.get('message')}")
        if e.status == 404 and not token:
            print(
                "Tip: If this is a private repository, you must provide a valid token."
            )
        return None


# --- Example Usage ---
if __name__ == "__main__":
    url = "https://github.com/RMIT-COSC2780-2973-IDM26/workshop-2-Alex-D-4089452/actions/runs/23228523313/job/67516475156"

    # Provide your GitHub Personal Access Token (PAT) via env var if needed
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

    try:
        annotations = get_job_annotations_pygithub(url, token=GITHUB_TOKEN)

        if annotations:
            print(f"\nFound {len(annotations)} annotation(s):")
            for idx, ann in enumerate(annotations, start=1):
                print(f"\n--- Annotation #{idx} ---")
                print(f"Level:       {ann.annotation_level}")
                print(f"Title:       {ann.title}")
                print(f"Message:     {ann.message}")
                print(f"File:        {ann.path}")
                print(f"Line Range:  {ann.start_line} to {ann.end_line}")
        elif annotations is not None:
            print("\nNo annotations found for this job run.")

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
