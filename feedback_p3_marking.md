Project {PROJECT_NO} FEEDBACK & RESULTS 💬
===========
{HEADER_TEXT}
|                                       |                           |
| :------------------------------------ | ------------------------: |
| **Student number:**                   |     {marking[STUDENT NO]} |
| **Student full name:**                | {marking[Preferred Name]} |
| **Github user:**                      |            {marking[GHU]} |
| **Git repo:**                         |       {marking[URL-REPO]} |
| **Timestamp submission:**             |      {marking[TIMESTAMP]} |
| **Commit marked:**                    |         {marking[COMMIT]} |
| **No of commits:**                    |       {marking[SE-NOCOM]} |
| **Commit ratio (<1 signal problems)** |       {marking[SE-RATIO]} |
| **Certified?**                        |  {marking[CERTIFICATION]} |
| **Days late tag (if any):**           |       {marking[DYS-LATE]} |
| **Days late certification (if any)**  |      {marking[LATE-CERT]} |

**NOTE:** Commit ratio is calculated pro-rata to the points/marks achieved. 
    
## Raw marks 🔎
| **Raw marks (earned / out of):** | {marking[RPOINTS]} | {TOTAL_POINTS} |
| :------------------------------- | ------------------ | -------------: |
| **Q1:**                          | {marking[Q1T]}     |              6 |
| **Q2:**                          | {marking[Q2T]}     |              1 |
| **Q3:**                          | {marking[Q3T]}     |              5 |
| **Q4:**                          | {marking[Q4T]}     |              5 |
| **Q5:**                          | {marking[Q5T]}     |              3 |
| **Q6:**                          | {marking[Q6T]}     |              1 |
| **Q7:**                          | {marking[Q7T]}     |              1 |
| **Q8:**                          | {marking[Q8T]}     |              3 |

## Development discount weights (if any) 🕵🏽‍♂️
| **Issues?**                              | {marking[SE-STATUS]} |
| :--------------------------------------- | -------------------: |
| **Bad/late tagging:**                    |    {marking[SE-TAG]} |
| **Merged feedback PR:**                  |  {marking[SE-PRMER]} |
| **Forced push:**                         | {marking[SE-FORCED]} |
| **Commits with invalid username:**       |  {marking[SE-GHUSR]} |
| **Printout side-effects (debug code?):** |  {marking[SE-LARGE]} |
| **Commit number/process:**               | {marking[SE-LOWRAT]} |
| **Commit messages:**                     |   {marking[SE-MESS]} |
| **Other quality issues:**                |   {marking[SE-OTHR]} |

**Note:** the above are _discount_ weights. So 0.3 means 30% discount on what was attracted. Empty means no discount 👍
    
## Summary of results 🏁
| .{spacing_table}.                                             |                       |
| :------------------------------------------------------------ | --------------------: |
| **Raw marks automarker:**                                     |    {marking[RPOINTS]} |
| **Development discount <br> (see above):**                    |  {marking[SE-WEIGHT]} |
| **Other discount weight (if any):**                           |   {marking[WEIGHT-M]} |
| **Total discount weight (if any):**                           |     {marking[WEIGHT]} |
| **Final weight adjustment <br> (1 - total discount weight):** | {marking[ADJ-WEIGHT]} |
| **Marks collected (out of {TOTAL_POINTS}):**                  |     {marking[POINTS]} |
| **Late penalty (if any):**                                    |   {marking[LATE-PEN]} |
| **Other mark adjustment:**                                    |     {marking[ADJUST]} |
| **FINAL MARKS (out of 100):**                                 |  **{marking[MARKS]}** |
| **Grade:**                                                    |  **{marking[GRADE]}** |
| **Grade feedback:**                                           |      {feedback_grade} |
| **Feedback automarking report:**                              |   See post above ☝️ |
| **Feedback, notes, observations (if any)**                    |            {feedback} |
| **Other feedback (if any)**                                   |     {feedback_manual} |


The final marks (out of 100) is calculated as follows: 📱

 * **FINAL MARKS** = (Raw marks * Final weight adjustment ) - Late penalty 

### 📢 Automarking Report & Feedback

---

We hope the feedback is clear and detailed.  The marking is **automated and objective**, based on **unit-testing best practices**, so there is limited room for subjective reconsideration.  

✅ If you believe there is a **factual error** in the marking (e.g. your code does *not* use a forbidden predicate but the report says it does), please **comment HERE in this PR👇🏾** with supporting evidence.  
❌ Do **not** send emails or make forum posts—requests outside this PR will not be processed.  
⚠️ Please do **not** ask for “reconsideration” of subjective matters (e.g. *“I think my code is better than what the report says”*). Messages begging for marks will not be answered.

⏰ Any challenges or requests must be made **within 5 working days** of this feedback. After that, marks will be considered final.  

---

### 🔍 Before Contacting Us

Please carefully review:

- The feedback in this report, both automarking and summary tables.
- The marking guide and project specification: all of it.  
- Your submitted code. The best learning happens when YOU 🫵 found the issue by yourself.  

➡️ Please respond here **only** if you have evidence of a factual error, or if something is genuinely unclear after you have carefully reviewed the resources above.

---

### ⚖️ Key Reminders: Process Development

- The goal is to show **evidence of your development process**. This is analogous with math assessments: we want to see your learning and thought journey, not just the final solution.  
- We used a **very low bound of {NO_COMMITS_EXPECTED} commits** for a perfect solution (scaled pro-rata on points achieved).  
- Fewer commits strongly suggests issues with the development process.  
- This expectation has been made clear multiple times (spec, lectorials, forum, feedback).  
- 🙏 Being “sorry” does not earn marks back.

---

🚀 **THANK YOU FOR YOUR SUBMISSION & COOPERATION, HOPE YOU ENJOYED THE PROJECT!** 🚀

Sebastian
