import logging


FINAL_MARKING = False   # final marking, no more resubmissions
HEADER_TEXT = ""
# HEADER_TEXT = "This has been remarked to account for missing information in the previous marking.\n"

# get the markdown message to post after the automarking report
with open("feedback_p2_report.md", "r", encoding="utf-8") as f:
    FEEDBACK_REPORT = f.read()

PROJECT_NO = 2
TOTAL_POINTS = 100   # as per spec weighting of points (not raw automarking points, which may be larger)
NO_COMMITS_EXPECTED = 8  # very low bar
RESUBMIT_FAQ_LINK = "https://github.com/RMIT-COSC1127-3117-AI25/AI25-DOC/blob/main/FAQ-PROJECTS.md#i-submitted-wrongly-eg-didnt-tag-correctly-and-is-now-after-the-due-date-can-you-consider-my-submission"
FIXED_SUBMISSION_MESSAGE = "The fixed submission must be done within 5 days of this messsage; no more extensions will be granted after that."

def just_left(s: str) -> str:
    """Justify string s to the left within width."""
    return '<div align="left">' + s + "</div>"

def result_feedback(marking_row: dict):
    """
    Genearte the feedback message based on the marking_row dictionary.
    The marking_row is the row in the marking spreadsheet and contains all the fields, including the NOTE-XXXX fields for feedback.
    
    This will be the table with the full results and the feedback comments.
    
    This does NOT include the report feedback (see FEEDBACK_REPORT), which is a separate message.
    """
    
    # join all the "NOTE-XXXX" fields into a single string
    feedback = "<br>".join([marking_row[x] for x in marking_row.keys() if "NOTE-" in x])
    feedback_manual = "<br>".join([marking_row[x] for x in marking_row.keys() if "MANUAL-" in x])
    # round float values to 2 decimal places
    for k in marking_row.keys():
        if type(marking_row[k]) == float:
            marking_row[k] = round(marking_row[k], 2)
            if marking_row[k].is_integer(): # drop decimals if none
                marking_row[k] = int(marking_row[k])
    with open("feedback_p2_marking.md", "r", encoding="utf-8") as f:
        message = f.read()
    
    message = message.format(
        PROJECT_NO=PROJECT_NO,
        HEADER_TEXT=HEADER_TEXT, 
        marking=marking_row, 
        TOTAL_POINTS=TOTAL_POINTS,
        feedback=just_left(feedback),
        feedback_grade=just_left(marking_row['FEEDBACK']),
        feedback_manual=just_left(feedback_manual),
        NO_COMMITS_EXPECTED=NO_COMMITS_EXPECTED,
        spacing_table="    "*22
        )
    return message


def check_submission(repo_id: str, marking_row: dict, batch: None, logger: logging.Logger):
    """Checks on the submission for the repo_id and returns a message and a skip flag, if applicable.

    The markign_repo is the row in the marking spreadsheet and may contain columns that signal problems with the submission.
    (e.g., no certification, no tag, etc.)
    """
    message = None
    skip = False
    skip_reason = ""

    # by default, do not skip, but any of the cases below will skip
    if batch is not None and marking_row["BATCH"] != batch:
        logger.warning(
            f"\t Repo {repo_id} is not in the batch {batch} to publish"
        )
        skip = True
        skip_reason = "not batch"
        return message, skip, skip_reason
    if marking_row["SKIP"]:
        logger.warning(
            f"\t Repo {repo_id} is flagged to be SKIPPED...: {marking_row['SKIP']}"
        )
        skip = True
        skip_reason = "skip flag"
        return message, skip, skip_reason
    if marking_row["DROPPED"]:
        logger.warning(f"\t Repo {repo_id} is DROPPED...: {marking_row['DROPPED']}")
        message = f"Dear @{repo_id}: you seem to not be enrolled in the course anymore, so no marking is performed. If this is an error, please let us know here. Otherwise, all the best!"
        skip = True
        skip_reason = "dropped_flag"
        return message, skip, skip_reason



    if FINAL_MARKING:
        # no more chances, this is it...
        if not marking_row["COMMIT"] or marking_row["CERTIFICATION"].upper() != "YES": 
            logger.warning(f"\t Repo {repo_id} has no tag submission and no certification!")
            message = (
                f"Dear @{repo_id}: incorrect or missing submission. No submission tag and/or no certification done; no marking as per spec. :cry: Please use this as a useful feedback and learning opportunity and submit correctly for next projects. You are responsible of submitting correctly as specified."
            )
            skip = True
            skip_reason = "no_commit_or_cert"
        return message, skip, skip_reason
    else:
        if not marking_row["COMMIT"] and marking_row["CERTIFICATION"].upper() != "YES": 
            logger.warning(f"\t Repo {repo_id} has no tag submission and no certification!")
            message = f"Dear @{repo_id}: no submission tag and no certification found, so nothing to mark. :cry: If you still want to submit (albeit with a discount), [check this]({RESUBMIT_FAQ_LINK}). All this was discussed a lot, including at lectorial; refer to slides. {FIXED_SUBMISSION_MESSAGE}"
            skip = True
            skip_reason = "no_commit_and_cert"
        elif not marking_row["COMMIT"]:
            logger.warning(f"\t Repo {repo_id} has no tag submission.")
            message = f"Dear @{repo_id}: no submission tag found, so nothing to mark. :cry: If you still want to submit (albeit with a discount), [check this]({RESUBMIT_FAQ_LINK}). Note this was discussed a lot, including at lectorial; refer to slides. {FIXED_SUBMISSION_MESSAGE}"
            skip = True
            skip_reason = "no_commit"
        elif marking_row["CERTIFICATION"].upper() != "YES":
            logger.warning(f"\t Repo {repo_id} has no certification.")
            message = f"Dear @{repo_id}: no certification found; no marking as per spec. :cry: If you still want to submit (albeit with a discount), please fill certification ASAP. Certification is in the submission instructions and has been discussed a lot, including at lectorials. {FIXED_SUBMISSION_MESSAGE}"
            skip = True
            skip_reason = "no_cert"
        return message, skip, skip_reason

    # should never get here
