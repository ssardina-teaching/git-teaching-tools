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
import os
try:
    import markdown
    import weasyprint
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


def extract_question_name(header):
    """Extract question name from header by taking everything up to the first full stop."""
    if '.' in header:
        return header.split('.')[0]
    return header


def load_submissions_dict(csv_file):
    """Load all submissions from CSV file as a dictionary with student number as key."""
    submissions = {}
    headers = []

    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        headers = reader.fieldnames

        for row in reader:
            student_number = row.get('Student number')
            if student_number:
                try:
                    submissions[int(student_number)] = row
                except ValueError:
                    # Skip rows with invalid student numbers
                    continue

    return submissions, headers


def get_question_columns(headers):
    """Get columns that contain questions (starting with 'E' and containing '.')."""
    question_columns = []
    for header in headers:
        # Look for headers that start with 'E' and contain a period (questions)
        if header.startswith('E') and '.' in header:
            question_columns.append(header)
    return question_columns


def group_questions_by_exercise(question_columns):
    """Group question columns by exercise number (E1, E2, etc.)."""
    exercises = {}
    for question_header in question_columns:
        question_name = extract_question_name(question_header)
        # Extract exercise number (E1, E2, E3, etc.)
        if question_name.startswith('E') and len(question_name) > 1:
            # Find where the exercise number ends
            i = 1
            while i < len(question_name) and question_name[i].isdigit():
                i += 1
            exercise_num = question_name[:i]  # E1, E2, E3, etc.

            if exercise_num not in exercises:
                exercises[exercise_num] = []
            exercises[exercise_num].append((question_header, question_name))

    # Sort exercises by number
    sorted_exercises = {}
    for exercise in sorted(exercises.keys(), key=lambda x: int(x[1:]) if x[1:].isdigit() else 999):
        sorted_exercises[exercise] = exercises[exercise]

    return sorted_exercises


def generate_markdown_table(submissions_dict, headers, student_number, points_dict=None, perfect_std=9999999) -> str:
    """Generate a markdown table with student answers for each question, grouped by exercise."""

    # Find the student's row
    student_row = submissions_dict.get(int(student_number))

    if not student_row:
        return None

    # Find the points row if points_dict is provided
    points_row = points_dict.get(int(student_number)) if points_dict else None

    # Get the full marks row (student number 1111111) for total points reference
    full_marks_row = points_dict.get(perfect_std) if points_dict else None

    # Get question columns
    question_columns = get_question_columns(headers)

    if not question_columns:
        return "No question columns found in the CSV file."

    # Group questions by exercise
    exercises = group_questions_by_exercise(question_columns)

    # Get student info
    student_name = f"{student_row.get('First name', '')} {student_row.get('Last name', '')}"
    student_score = student_row.get('Score', 'N/A')
    timestamp = student_row.get('Timestamp', 'N/A')

    # Generate markdown with separate tables for each exercise
    markdown = f"# Student Answers - {student_name} - Student no: {student_number}\n\n"
    markdown += f"**Submitted:** {timestamp}\n\n"
    markdown += f"**Score:** {student_score}\n\n"

    for exercise_num, questions in exercises.items():
        # Add exercise header
        markdown += f"## Exercise {exercise_num[1:]} ({exercise_num})\n\n"

        # Add table header (include points column if points data is available)
        if points_row:
            markdown += "| Question | Answer | Points |\n"
            markdown += "|----------|--------|--------|\n"
        else:
            markdown += "| Question | Answer |\n"
            markdown += "|----------|--------|\n"

        # Add questions for this exercise
        for question_header, question_name in questions:
            answer = student_row.get(question_header, '').strip()

            # Handle empty answers
            if not answer:
                answer = "*No answer provided*"

            # Escape pipe characters in answers to avoid breaking the table
            answer = answer.replace('|', '\\|')

            # Get points if available
            if points_row:
                student_pts = points_row.get(question_header, 'N/A')

                points_display = f"{student_pts}"

                # add total marks out of if available
                if full_marks_row:
                    total_points = full_marks_row.get(question_header, 'N/A')
                    points_display += f" / {total_points}"

                markdown += f"| {question_name} | {answer} | {points_display} |\n"
            else:
                markdown += f"| {question_name} | {answer} |\n"

        markdown += "\n"  # Add space between exercise tables

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
    parser.add_argument('csv_file', help='Path to the CSV file with form submissions')
    parser.add_argument('student_number', nargs='+', help='Student number(s) to search for (can specify multiple)')
    parser.add_argument('report_folder', help='Folder to save reports')
    parser.add_argument('-p', '--points', help='Path to the CSV file with points (optional)')
    parser.add_argument('-ps', '--perfect',
                        type=int,
                        default=9999999,
                        help='Number of perfect students (to get total points per question) Default: %(default)s')
    args = parser.parse_args()
    print(args)

    root_dir = Path(args.report_folder)

    try:
        # Load CSV data once as dictionary
        submissions_dict, headers = load_submissions_dict(args.csv_file)

        # Load points data if provided
        points_dict = None
        if args.points:
            points_dict, _ = load_submissions_dict(args.points)

        # Process each student number
        n = len(args.student_number)
        for i, student_num in enumerate(args.student_number):
            print(f"===> Processing student number {i+1}/{n}: {student_num}")
            try:
                student_number = int(student_num)
            except ValueError:
                print(f"Error: Invalid student number '{student_num}'. Skipping.")
                continue

            markdown_output = generate_markdown_table(submissions_dict, headers, student_number, points_dict=points_dict, perfect_std=args.perfect)

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
