import logging
from pathlib import Path


#########################
# CORE CONFIGURATION
#########################
FINAL_MARKING = False   # final marking, no more resubmissions
PROJECT_NO = 3
TOTAL_POINTS = 25   # as per spec weighting of points (sum of all question points, Q1+...+Qn)
NO_COMMITS_EXPECTED = 11  # very low bar
RESUBMIT_FAQ_LINK = "https://github.com/RMIT-COSC1127-3117-AI25/AI25-DOC/blob/main/FAQ-PROJECTS.md#i-submitted-wrongly-eg-didnt-tag-correctly-and-is-now-after-the-due-date-can-you-consider-my-submission"
FIXED_SUBMISSION_MESSAGE = "The fixed submission must be done **within 5 days of this messsage**; no more extensions will be granted after that. Do not send emails or post on the forum, any follow ups should be done in this PR 👇."

# main feedback template in markdown format
FILE_FEEDBACK="feedback_p3_marking.md"


########################
# OPTIONAL CONFIGURATION
########################
# optional text before and after automarking report
FILE_FEEDBACK_REPORT_BEFORE="feedback_p3_report_before.md"
FILE_FEEDBACK_REPORT_AFTER="feedback_p3_report_after.md"

# default: NO MESSAGES BEFORE AND AFTER REPORT
FILE_FEEDBACK_REPORT_BEFORE=None
# FILE_FEEDBACK_REPORT_AFTER=None

# HEADER_TEXT = "This has been remarked to account for missing information in the previous marking.\n"
# HEADER_TEXT = "Well done, you did fantastic work in this project! 💯 🎉\n"
# HEADER_TEXT = "Well done, you did fantastic work in this project!  🎉\n"

HEADER_TEXT = ""

if FILE_FEEDBACK_REPORT_BEFORE is not None and Path(FILE_FEEDBACK_REPORT_BEFORE).exists():
    # get the markdown message to post after the automarking report
    with open(FILE_FEEDBACK_REPORT_BEFORE, "r", encoding="utf-8") as f:
        FEEDBACK_REPORT_BEFORE = f.read()
else:
    FEEDBACK_REPORT_BEFORE = "" # no remark information
if FILE_FEEDBACK_REPORT_AFTER is not None and Path(FILE_FEEDBACK_REPORT_AFTER).exists():
    with open(FILE_FEEDBACK_REPORT_AFTER, "r", encoding="utf-8") as f:
        FEEDBACK_REPORT_AFTER = f.read()
else:
    FEEDBACK_REPORT_AFTER = "" # no remark information



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
    with open(FILE_FEEDBACK, "r", encoding="utf-8") as f:
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
                f"❌ Dear @{repo_id}: incorrect or missing submission. No submission tag and/or no certification done; no marking as per spec. 😢 Please use this as a useful feedback and learning opportunity and submit correctly for next projects. You 🫵 are responsible of submitting correctly as specified."
            )
            skip = True
            skip_reason = "no_commit_or_cert"
        return message, skip, skip_reason
    else:
        if not marking_row["COMMIT"] and marking_row["CERTIFICATION"].upper() != "YES": 
            logger.warning(f"\t Repo {repo_id} has no tag submission and no certification!")

            message = f"❌ Dear @{repo_id}: no submission tag and no certification were found, so no marking can be provided as per the project specification. 😢 \n If you still wish to submit (albeit with discount penalty), please tag and complete the certification **as soon as possible**, [check this]({RESUBMIT_FAQ_LINK}). The tagging and certification were detailed in the submission instructions and have been discussed extensively, including during lectorials. {FIXED_SUBMISSION_MESSAGE}"

            skip = True
            skip_reason = "no_commit_and_cert"
        elif not marking_row["COMMIT"]:
            logger.warning(f"\t Repo {repo_id} has no tag submission.")

            message = f"❌ Dear @{repo_id}: no submission tag was found, so no marking can be provided as per the project specification. 😢 \n If you still wish to submit (albeit with discount penalty), please tag **as soon as possible**, [check this]({RESUBMIT_FAQ_LINK}).  {FIXED_SUBMISSION_MESSAGE}"

            skip = True
            skip_reason = "no_commit"
        elif marking_row["CERTIFICATION"].upper() != "YES":
            logger.warning(f"\t Repo {repo_id} has no certification.")
            
            message = f"❌ Dear @{repo_id}: no certification was found, so no marking can be provided as per the project specification. 😢 \n If you still wish to submit (albeit with discount penalty), please complete the certification **as soon as possible**. The certification is detailed in the submission instructions and has been discussed extensively, including during lectorials. {FIXED_SUBMISSION_MESSAGE}"
            
            skip = True
            skip_reason = "no_cert"
        return message, skip, skip_reason

    # should never get here
