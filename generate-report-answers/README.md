# Student Answer Generator

This Python script generates a markdown table with individual student answers from a CSV file containing exam form submissions.

## Features

- Extracts student answers for all exam questions
- **Groups questions by exercise** (E1, E2, E3, etc.) with separate subtables for each exercise
- Creates formatted markdown tables with clear exercise organization
- **Generate PDF output** with professional styling and formatting
- Shows student name, number, and score
- Handles missing answers gracefully
- Can output to file or stdout

## Usage

### Basic usage (output to console)

```bash
python generate_student_answers.py form-submissions.csv 1234567
```

### Save to markdown file

```bash
python generate_student_answers.py form-submissions.csv 1234567 -o student_answers.md
```

### Generate PDF output

```bash
# Generate PDF with default filename
python generate_student_answers.py form-submissions.csv 1234567 --pdf

# Generate PDF with custom filename
python generate_student_answers.py form-submissions.csv 1234567 --pdf -o custom_name.pdf
```

### Get help

```bash
python generate_student_answers.py --help
```

## Arguments

- `csv_file`: Path to the CSV file with form submissions
- `student_number`: Student number to search for
- `-o, --output`: Optional output file (prints to stdout if not provided)
- `--pdf`: Generate PDF output instead of markdown

## PDF Requirements

To generate PDF output, you need to install additional packages:

```bash
pip install markdown weasyprint
```

**Note**: WeasyPrint may require additional system dependencies depending on your operating system. If you encounter issues, please refer to the [WeasyPrint installation guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation).

### PDF Features

- Professional styling with proper fonts and spacing
- Table formatting with alternating row colors
- Exercise sections with clear headers
- Automatic page breaks when needed
- High-quality output suitable for printing or sharing

## CSV Format Requirements

The script expects a CSV file with:

- A header row containing question titles in the format "E1(a)i. Description"
- A column named "Student number" containing student IDs
- Columns named "First name", "Last name", and "Score" for student information
- Question columns starting with 'E' and containing a period

## Question Name Extraction

Question names are extracted by taking all characters up to the first period (full stop). For example:

- "E1(a)i. Provide your answer(s) here." becomes "E1(a)i"
- "E2(b). Provide your answer(s) here." becomes "E2(b)"

## Output Format

The script generates a markdown document with:

- Student name and number as main header
- Student's score displayed prominently
- **Separate sections for each exercise** (Exercise 1, Exercise 2, etc.)
- Each exercise section contains a two-column table with Question and Answer columns
- Questions are grouped by exercise number (E1, E2, E3, etc.) for better organization
- Proper markdown formatting with escaped special characters

### Example Output Structure

```markdown
# Student Answers - John Doe (Student #1234567)

**Score:** 85 / 125

## Exercise 1 (E1)
| Question | Answer |
|----------|--------|
| E1(a)i   | AFBCG  |
| E1(a)ii  | AFCBG  |
...

## Exercise 2 (E2)
| Question | Answer |
|----------|--------|
| E2(a)i   | B, E, F |
...
```
