import logging

HEADER__TEXT = ""
HEADER__TEXT = "This has been remarked to account for missing information in the previous marking.\n"
FEEDBACK_MESSAGE = """

-------------------------
Your code has been automarked for technical correctness and your grades are now preliminary registered!

Please note the following:

- We will be running code similarity checks, as well as inspecting reports and code manually, in an ongoing basis for all the projects. We reserve the right to adjust the marks or to have a demo meeting with you, if necessary.
- The total points above is raw and does not reflect the weighting of each question (as per spec.).

Thanks for your submission & hope you enjoyed and learnt from this Pacman Search project!

Sebastian
"""
PROJECT_NO = 1
TOTAL_POINTS = 38  # as per spec weighting of points (not raw automarking points, which may be larger)
NO_COMMITS_EXPECTED = 13
FIXED_SUBMISSION_MESSAGE = "The fixed submission must be done before **August 29th, 12pm**; no more extensions will be granted after that."

FEEDBACK_ENABLED = False
FEEDBACK_ENABLED = True

FINAL_MARKING = False


def just_left(s: str) -> str:
    """Justify string s to the left within width."""
    return '<div align="left">' + s + "</div>"


def report_feedback(marking):
    # join all the "NOTE-XXXX" fields into a single string
    feedback = "<br>".join([marking[x] for x in marking.keys() if "NOTE-" in x])

    # round float values to 2 decimal places
    for k in marking.keys():
        if type(marking[k]) == float:
            marking[k] = round(marking[k], 2)

    return f"""Project {PROJECT_NO} FEEDBACK & RESULTS 💬
===========
{HEADER__TEXT}
|                                          |                             |
|:-----------------------------------------|----------------------------:|
|**Student number:**                         | {marking['STUDENT NO']} |
|**Student full name:**                      | {marking['Preferred Name']} |
|**Github user:**                            | {marking['GHU']} |
|**Git repo:**                               | {marking['URL-REPO']} |
|**Timestamp submission:**                   | {marking['TIMESTAMP']} |
|**Commit marked:**                          | {marking['COMMIT']} |
|**No of commits:**                          | {marking['SE-NOCOM']} |
|**Commit ratio (<1 signal problems)**       | {marking['SE-RATIO']} |
|**Days late tag (if any):**                 | {marking['DYS-LATE']} |
|**Certified?**                              | {marking['CERTIFICATION']} |
|**Days late certification (if any)**        | {marking['LATE-CERT']} |

**NOTE:** Commit ratio is calculated pro-rata to the points achieved. 
    
## Raw points 🔎
|**Raw points (earned / out of):**      | {marking['RPOINTS']}  | {TOTAL_POINTS} |
|:--------------------------------------|-----------------------|---:|
|**Q1:**                                | {marking['Q1T']}      | 3  |
|**Q2:**                                | {marking['Q2T']}      | 3  |
|**Q3:**                                | {marking['Q3T']}      | 3  |
|**Q4:**                                | {marking['Q4T']}      | 3  |
|**Q5:**                                | {marking['Q5T']}      | 3  |
|**Q6:**                                | {marking['Q6T']}      | 3  |
|**Q7:**                                | {marking['Q7T']}      | 5  |
|**Q8:**                                | {marking['Q8T']}      | 3  |
|**Q9:**                                | {marking['Q9T']}      | 8  |
|**Q10:**                               | {marking['Q10T']}     | 4  |

    
## Software Engineering (SE) (discount) weights (if any) 🕵🏽‍♂️
|**Issues?**                                | {marking['SE-STATUS']} |
|:------------------------------------------|---------------------:|
|**Bad/late tagging:**                      | {marking['SE-TAG']} |
|**Merged feedback PR:**                    | {marking['SE-PRMER']} |
|**Forced push:**                           | {marking['SE-FORCED']} |
|**Commits with invalid username:**         | {marking['SE-GHUSR']} |
|**Printout side-effects (debug code?):**   | {marking['SE-LARGE']} |
|**Commit number/process:**                 | {marking['SE-LOWRAT']} |
|**Other quality issues:**                  | {marking['SE-OTHR']} |
    
## Summary of results 🏁
| .{"    "*22}.    |                       |
|:------------------------------------------|----------------------:|
|**Raw points collected:**                  | {marking['RPOINTS']}  |
|**Other discount weight (if any):**        | {marking['WEIGHT-M']}   |
|**Total weight adjustment <br> (1 if none; read below):**   | {marking['WEIGHT']}   |
|**Final points (out of {TOTAL_POINTS}):**  | {marking['POINTS']}  |
|**Raw marks (out of 100):**                | {marking['RAW-MARKS']}    |
|**Late penalty (10/day, if any):**         | {marking['LATE-PEN']} |
|**Final marks (out of 100):**              | **{marking['MARKS']}**    |
|**Grade:**                                 | **{marking['GRADE']}**    |
|**Grade feedback:**                        | {just_left(marking['FEEDBACK'])}    |
|**Feedback report:**                       | See comment before :-)|
|**Feedback, notes, observations (if any)** | {just_left(feedback)}      |
|**Other feedback (if any)**                | {just_left(marking['MANUAL-FEEDBACK'])} |


The final marks (out of 100) is calculated as follows: 📱

* **RAW MARKS** = ((RAW_POINTS / TOTAL_POINTS)*TOTAL_WEIGHT_ADJUSTMENT)*100
* **FINAL MARKS** = RAW MARKS - LATE PENALTY

For more information on marking scheme, refer to post [#224](https://edstem.org/au/courses/25332/discussion/2880419).

Hope the above feedback is clear and detailed🤞, but if you spot any factual error in the marking or you really need clarification (after carefully analysing the feedback), please **post HERE in this PR** 👇🏾: _do not send email or make posts in the forum_.

Remember the SE/GIT development aims to have minimal **evidence of the process towards the solution in your development**. The expected commits is a bare minimum that serves as _proxy_ to signal a problem, not an aim in itself (that is why it is so low). For this project, we used a **very low bound of {NO_COMMITS_EXPECTED} commits** for a _perfect solution_ (pro-rata on points achieved); less than strongly suggests problem with development.

Sebastian
"""


def check_submission(repo_id: str, marking_repo: dict, logger: logging.Logger):
    """Checks on the submission for the repo_id and returns a message and a skip flag, if applicable.

    The markign_repo is the row in the marking spreadsheet and may contain columns that signal problems with the submission.
    (e.g., no certification, no tag, etc.)
    """
    message = None
    skip = False
    skip_reason = ""

    # by defeault, do not skip, but any of the cases below will skip
    if marking_repo["SKIP"]:
        logger.warning(
            f"\t Repo {repo_id} is flagged to be SKIPPED...: {marking_repo['SKIP']}"
        )
        skip = True
        skip_reason = "skip flag"
        return message, skip, skip_reason

    if marking_repo["DROPPED"]:
        logger.warning(f"\t Repo {repo_id} is DROPPED...: {marking_repo['DROPPED']}")
        message = f"Dear @{repo_id}: you seem to not be enrolled in the course anymore, so no marking is performed. If this is an error, please let us know here. Otherwise, all the best!"
        skip = True
        skip_reason = "dropped_flag"
        return message, skip, skip_reason

    if FINAL_MARKING:
        # no more chances...
        if not marking_repo["COMMIT"] or marking_repo["CERTIFICATION"].upper() != "YES":
            logger.warning(
                f"\t Repo {repo_id} has no tag submission and no certification!"
            )
            message = f"Dear @{repo_id}: incorrect or missing submission. No submission tag and/or no certification done; no marking as per spec. :cry: Please use this as a useful feedback and learning opportunity and submit correctly for next projects. "
            skip = True
            skip_reason = "no_commit_or_cert"
        return message, skip, skip_reason
    else:
        if (
            not marking_repo["COMMIT"]
            and marking_repo["CERTIFICATION"].upper() != "YES"
        ):
            logger.warning(
                f"\t Repo {repo_id} has no tag submission and no certification!"
            )
            message = f"Dear @{repo_id}: no submission tag and no certification found, so nothing to mark. :cry: If you still want to submit (albeit with a discount), [check this](https://tinyurl.com/29h2on8k). All this was discussed a lot, including at lectorial; refer to slides. {FIXED_SUBMISSION_MESSAGE}"
            skip = True
            skip_reason = "no_commit_and_cert"
        if not marking_repo["COMMIT"]:
            logger.warning(f"\t Repo {repo_id} has no tag submission.")
            message = f"Dear @{repo_id}: no submission tag found, so nothing to mark. :cry: If you still want to submit (albeit with a discount), [check this](https://tinyurl.com/29h2on8k). Note this was discussed a lot, including at lectorial; refer to slides. {FIXED_SUBMISSION_MESSAGE}"
            skip = True
            skip_reason = "no_commit"
        elif marking_repo["CERTIFICATION"].upper() != "YES":
            logger.warning(f"\t Repo {repo_id} has no certification.")
            message = f"Dear @{repo_id}: no certification found; no marking as per spec. :cry: If you still want to submit (albeit with a discount), please fill certification ASAP. Certification is in the submission instructions and has been discussed a lot, including at lectorials. {FIXED_SUBMISSION_MESSAGE}"
            skip = True
            skip_reason = "no_cert"
        return message, skip, skip_reason

    # should never get here
