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

**NOTE:** Commit ratio is calculated pro-rata to the points achieved. 
    
## Raw points 🔎
| **Raw points (earned / out of):** | {marking[RPOINTS]} | {TOTAL_POINTS} |
| :-------------------------------- | -------------------- | -------------: |
| **Q0:**                           | {marking[Q1T]}     |             15 |
| **Q1:**                           | {marking[Q2T]}     |             30 |
| **Q2:**                           | {marking[Q3T]}     |             25 |
| **Q3:**                           | {marking[Q4T]}     |             30 |
    
## Software Engineering (SE) (discount) weights (if any) 🕵🏽‍♂️
| **Issues?**                              | {marking[SE-STATUS]} |
| :--------------------------------------- | ---------------------: |
| **Bad/late tagging:**                    |    {marking[SE-TAG]} |
| **Merged feedback PR:**                  |  {marking[SE-PRMER]} |
| **Forced push:**                         | {marking[SE-FORCED]} |
| **Commits with invalid username:**       |  {marking[SE-GHUSR]} |
| **Printout side-effects (debug code?):** |  {marking[SE-LARGE]} |
| **Commit number/process:**               | {marking[SE-LOWRAT]} |
| **Other quality issues:**                |   {marking[SE-OTHR]} |
    
## Summary of results 🏁
| .{spacing_table}.                                             |                                  |
| :-------------------------------------------------------- | -------------------------------: |
| **Raw points collected:**                                 |             {marking[RPOINTS]} |
| **Other discount weight (if any):**                       |            {marking[WEIGHT-M]} |
| **Total weight adjustment <br> (1 if none; read below):** |              {marking[WEIGHT]} |
| **Final points (out of {TOTAL_POINTS}):**                 |              {marking[POINTS]} |
| **Raw marks (out of 100):**                               |           {marking[RAW-MARKS]} |
| **Late penalty (if any):**                                |            {marking[LATE-PEN]} |
| **Final marks (out of 100):**                             |           **{marking[MARKS]}** |
| **Grade:**                                                |           **{marking[GRADE]}** |
| **Grade feedback:**                                       | {feedback_grade} |
| **Feedback report:**                                      |           See comment before :-) |
| **Feedback, notes, observations (if any)**                |            {feedback} |
| **Other feedback (if any)**                               |     {feedback_manual} |


The final marks (out of 100) is calculated as follows: 📱

* **RAW MARKS** = ((RAW_POINTS / TOTAL_POINTS)*TOTAL_WEIGHT_ADJUSTMENT)*100
* **FINAL MARKS** = RAW MARKS - LATE PENALTY

### 📢 Automarking Report & Feedback

For details about the marking scheme, see:  
- [Ed post #418](https://edstem.org/au/courses/25332/discussion/2970696)  
- [Marking guide explanation](https://github.com/RMIT-COSC1127-3117-AI25/AI25-DOC/blob/main/MARKING-P2.md)

---

We hope the feedback is clear and detailed.  The marking is **automated and objective**, based on **unit-testing best practices**, so there is limited room for subjective reconsideration.  

✅ If you believe there is a **factual error** in the marking (e.g. your code does *not* use a forbidden predicate but the report says it does), please **comment HERE in this PR👇🏾** with supporting evidence.  
❌ Do **not** send emails or make forum posts—requests outside this PR will not be processed.  
⚠️ Please do **not** ask for “reconsideration” of subjective matters (e.g. *“I think my code is better than what the report says”*). Messages begging for marks will not be answered.  

⏰ Any challenges or requests must be made **within 5 working days** of this feedback. After that, marks will be considered final.  

---

### 🔍 Before Contacting Us

Please carefully review:

- The feedback in this report.
- The marking guide and Ed post above.  
- Your submitted code. The best learning happens when YOU 🫵 found the issue by yourself.  

---

### ⚖️ Key Reminders

1. **SE/Git Development**  
   - The goal is to show **evidence of your development process**.  
   - We used a **very low bound of {NO_COMMITS_EXPECTED} commits** for a perfect solution (scaled pro-rata on points achieved).  
   - Fewer commits strongly suggests issues with the development process.  
   - This expectation has been made clear multiple times (spec, lectorials, forum, feedback).  
   - 🙏 Being “sorry” does not earn marks back.

2. **Language Restrictions**  
   - The spec was explicit about which Prolog built-ins are allowed and which are forbidden (see *Language restrictions and guidelines*).  
   - Any test using a forbidden predicate will score **0 points** for that item, regardless of other functionality.  
   - We have already been lenient in not disqualifying the whole question.  
   - 🙏 Again, apologies are not a substitute for following the rules.  

---

➡️ Please respond here **only** if you have evidence of a factual error, or if something is genuinely unclear after you have carefully reviewed the resources above.

🚀 **THANK YOU FOR YOUR SUBMISSION & COOPERATION, HOPE YOU ENJOYED THE PROJECT!** 🚀

Sebastian