#!/usr/bin/env python3
"""
Script to generate a markdown table with student answers for each question.
Takes a CSV file and a student number as input.

Usage:
python generate_student_answers.py <csv_file> <student_number>
"""

import csv
from pathlib import Path
import sys
import argparse
import regex as re
try:
    import markdown
    import weasyprint
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


COL_STD_NO = 'Student number'
COL_TIMESTAMP = 'Timestamp'
COL_FIRST_NAME = 'First name'
COL_LAST_NAME = 'Last name'
COL_SCORE = 'Score'
COLS_SPECIAL = {COL_STD_NO, COL_TIMESTAMP, COL_FIRST_NAME, COL_LAST_NAME, COL_SCORE}

def extract_question_name(header):
    """Extract question name from header by taking everything up to the first full stop."""
    if '.' in header:
        return header.split('.')[0]
    return header


def extract_question_id(header):
    """Extract question id from header and question number.
    If header is 'E2(b)ii.Enter your answer.' it return (E2(b)ii, 2)"""
    match = re.match(r"(E(\d+).*?)\.", header)

    if match:
        question_id = match.group(1)
        question_num = int(match.group(2))
        return question_id, question_num
    return None, None


def load_submissions_dict(csv_file):
    """Load all submissions from CSV file as a dictionary with student number as key."""
    submissions = {}

    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for row in reader:
            try:
                student_number = int(row.get(COL_STD_NO))

                # extract answers from this student for each question
                answers = dict()
                answers["Timestamp"] = row.get("Timestamp", "")
                answers["First name"] = row.get("First name", "")
                answers["Last name"] = row.get("Last name", "")
                answers["Score"] = row.get("Score", "")

                for key in row:
                    question_id, _ = extract_question_id(key)
                    if question_id is not None:
                        answers[question_id] = row[key]

                submissions[student_number] = answers
            except ValueError:
                # Skip rows with invalid student numbers
                continue

    return submissions


def get_exercises(answers: dict):
    """Divide question IDs into exercises based on question numbers.

    questions[question_no] = [question_id1, question_id2, ...]
    """
    questions = dict()
    for question_id in answers:
        # Look for headers that start with 'E' and contain a period (questions)
        if question_id in COLS_SPECIAL:
            continue
        question_no = int(re.findall(r"\d+", question_id)[0])
        if question_no not in questions:
            questions[question_no] = [question_id]
        else:
            questions[question_no].append(question_id)
    return questions




def generate_markdown_table(submissions_dict, student_number, points_dict=None, perfect_std=9999999, additional_markdown="") -> str:
    """Generate a markdown table with student answers for each question, grouped by exercise."""

    # Find the student's row
    student_dict = submissions_dict.get(student_number)

    if not student_dict:
        return None

    # Find the points row if points_dict is provided
    points_row = points_dict.get(student_number, None)

    # Get the full marks row (student number 1111111) for total points reference
    full_marks_row = points_dict.get(perfect_std, None)

    # Get question columns
    print(next(iter(submissions_dict.values())))

    # get dictionary of exercises (each key is a number, value is list of question ids)
    exercises = get_exercises(next(iter(submissions_dict.values())))

    if not exercises:
        return "No question columns found in the CSV file."

    # Get student info
    student_name = f"{student_dict.get('First name', '')} {student_dict.get('Last name', '')}"
    student_score = student_dict.get('Score', 'N/A')
    timestamp = student_dict.get('Timestamp', 'N/A')

    # Generate markdown with separate tables for each exercise
    markdown = f"# Student Answers: {student_name} - {student_number}\n\n"
    markdown += f"**Submitted:** {timestamp}\n\n"
    markdown += f"**Score:** {student_score}\n\n"

    for exercise_no in exercises:
        # Add exercise header
        markdown += f"## Exercise {exercise_no}\n\n"

        # Add table header (include points column if points data is available)
        if points_row:
            markdown += "| Question | Answer | Points |\n"
            markdown += "|----------|--------|--------|\n"
        else:
            markdown += "| Question | Answer |\n"
            markdown += "|----------|--------|\n"

        # Add questions for this exercise
        for question_id in exercises[exercise_no]:
            answer = student_dict.get(question_id, '').strip()

            # Handle empty answers
            if not answer:
                answer = "*No answer provided*"

            # Escape pipe characters in answers to avoid breaking the table
            answer = answer.replace('|', '\\|')

            # Get points if available
            if points_row:
                student_pts = points_row.get(question_id, 'N/A')

                points_display = f"{student_pts}"

                # add total marks out of if available
                if full_marks_row:
                    total_points = full_marks_row.get(question_id, 'N/A')
                    points_display += f" / {total_points}"

                markdown += f"| {question_id} | {answer} | {points_display} |\n"
            else:
                markdown += f"| {question_id} | {answer} |\n"

        markdown += "\n"  # Add space between exercise tables

    # Add additional markdown content if provided
    if additional_markdown.strip():
        markdown += "\n---\n\n"  # Add separator
        markdown += additional_markdown
        markdown += "\n"

    return markdown


def convert_to_pdf(markdown_content, pdf_path : Path):
    """Convert markdown content to PDF using weasyprint."""
    if not PDF_AVAILABLE:
        raise ImportError("PDF generation requires 'markdown' and 'weasyprint' packages. Install with: pip install markdown weasyprint")

    # Convert markdown to HTML
    html_content = markdown.markdown(markdown_content, extensions=['tables'])

    # Add compact CSS styling for PDF with smaller fonts and tighter spacing
    css_style = """
    <style>
    body {
        font-family: 'Arial', sans-serif;
        font-size: 10px;
        margin: 15mm;
        line-height: 1.3;
    }
    h1 {
        color: #2c3e50;
        font-size: 16px;
        border-bottom: 1px solid #3498db;
        padding-bottom: 5px;
        margin-bottom: 10px;
        margin-top: 0;
    }
    h2 {
        color: #34495e;
        font-size: 12px;
        margin-top: 15px;
        margin-bottom: 8px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 8px 0 15px 0;
        font-size: 9px;
    }
    th, td {
        border: 1px solid #bdc3c7;
        padding: 4px 6px;
        text-align: left;
        vertical-align: top;
    }
    th {
        background-color: #ecf0f1;
        font-weight: bold;
        font-size: 9px;
    }
    tr:nth-child(even) {
        background-color: #f8f9fa;
    }
    p {
        margin: 5px 0;
    }
    </style>
    """

    # Combine CSS and HTML
    full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'>{css_style}</head><body>{html_content}</body></html>"

    # Generate PDF
    weasyprint.HTML(string=full_html).write_pdf(pdf_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate markdown table with student answers from CSV')
    parser.add_argument('csv_answers', help='Path to the CSV file with form submission answers')
    parser.add_argument('student_number', nargs='+', help='Student number(s) to search for (can specify multiple)')
    parser.add_argument('report_folder', help='Folder to save reports')
    parser.add_argument('-p', '--points', help='Path to the CSV file with points (optional)')
    parser.add_argument('-pp', '--perfect',
                        type=int,
                        default=9999999,
                        help='Number of perfect students (to get total points per question) Default: %(default)s')
    parser.add_argument('-a', '--additional', help='Path to markdown file with additional content to append to reports (optional)')
    args = parser.parse_args()
    print(args)

    root_dir = Path(args.report_folder)

    try:
        # Load CSV data once as dictionary
        answers_dict = load_submissions_dict(args.csv_answers)

        # Load points data if provided
        points_dict = None
        if args.points:
            points_dict = load_submissions_dict(args.points)


        # Load additional markdown content if provided
        additional_markdown = ""
        if args.additional:
            try:
                with open(args.additional, 'r', encoding='utf-8') as f:
                    additional_markdown = f.read()
            except FileNotFoundError:
                print(f"Warning: Additional markdown file '{args.additional}' not found. Skipping additional content.")
            except Exception as e:
                print(f"Warning: Could not read additional markdown file '{args.additional}': {e}. Skipping additional content.")

        # Process each student number
        n = len(args.student_number)
        for i, student_num in enumerate(args.student_number):
            print(f"===> Processing student number {i+1}/{n}: {student_num}")
            try:
                student_number = int(student_num)
            except ValueError:
                print(f"Error: Invalid student number '{student_num}'. Skipping.")
                continue

            markdown_output = generate_markdown_table(answers_dict, student_number, points_dict=points_dict, perfect_std=args.perfect, additional_markdown=additional_markdown)

            if markdown_output is None:
                print(f"Student number {student_number} not found in the CSV file. Skipping...")
                continue

            # Generate PDF report file
            pdf_path = Path( root_dir / f"report_{student_number}.pdf")
            convert_to_pdf(markdown_output, pdf_path)
            print(f"PDF saved to {pdf_path}")

            # Generate markdown report file
            md_path = pdf_path.with_suffix(".md")
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(markdown_output)
            print(f"Markdown table saved to {md_path}")
    except FileNotFoundError:
        print(f"Error: File '{args.csv_file}' not found.")
        sys.exit(1)
    except ImportError as e:
        print(f"Error: {e}")
        print("To install required packages for PDF generation, run:")
        print("pip install markdown weasyprint")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
