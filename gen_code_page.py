#!/usr/bin/env python3
"""
Generate a PDF of attendance codes for printing and cutting.

Reads a text file with one code per line and produces a PDF where each code
is displayed in a box, laid out in 3 columns × 18 rows per page.
Print the PDF and cut out each box to hand to students.

This can be used with EdStem Attendance Tracker feature (2026)

Usage:
    python generate_attendance_codes.py <codes_file> [output.pdf]

Check example codes in code-attendance.txt, and run:

    $ python gen_code_page.py code-attendance.txt
    $ PDF written to: code-attendance.pdf  (126 codes, 3 page(s))
"""
import argparse
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

COLS = 3
ROWS = 18
CODES_PER_PAGE = COLS * ROWS

# Page margins (mm)
MARGIN_H = 10 * mm
MARGIN_V = 10 * mm

# Gap between boxes (mm) — space to cut along
GAP = 4 * mm

# Font
FONT_NAME = "Courier-Bold"
FONT_SIZE = 16


def load_codes(path: Path) -> list[str]:
    codes = [line.strip() for line in path.read_text().splitlines()]
    return [c for c in codes if c]


def draw_page(
    c: canvas.Canvas, page_codes: list[str], page_w: float, page_h: float
) -> None:
    usable_w = page_w - 2 * MARGIN_H
    usable_h = page_h - 2 * MARGIN_V

    # Each cell slot includes a trailing gap; the box fills the slot minus that gap
    slot_w = usable_w / COLS
    slot_h = usable_h / ROWS
    box_w = slot_w - GAP
    box_h = slot_h - GAP

    for idx, code in enumerate(page_codes):
        col = idx % COLS
        row = idx // COLS

        # ReportLab y=0 is bottom; we fill rows top-to-bottom
        # Offset by half the gap to centre the box within the slot
        x = MARGIN_H + col * slot_w + GAP / 2
        y = page_h - MARGIN_V - (row + 1) * slot_h + GAP / 2

        # Draw cell border
        c.rect(x, y, box_w, box_h)

        # Centre the code text in the box
        c.setFont(FONT_NAME, FONT_SIZE)
        text_x = x + box_w / 2
        text_y = y + box_h / 2 - FONT_SIZE * 0.35  # rough vertical centre
        c.drawCentredString(text_x, text_y, code)


def generate_pdf(codes: list[str], output_path: Path) -> None:
    page_w, page_h = A4
    c = canvas.Canvas(str(output_path), pagesize=A4)

    # Split codes into pages
    for page_start in range(0, len(codes), CODES_PER_PAGE):
        page_codes = codes[page_start : page_start + CODES_PER_PAGE]
        draw_page(c, page_codes, page_w, page_h)
        c.showPage()

    c.save()
    print(
        f"PDF written to: {output_path}  ({len(codes)} codes, "
        f"{-(-len(codes) // CODES_PER_PAGE)} page(s))"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a printable PDF of attendance codes."
    )
    parser.add_argument(
        "codes_file", type=Path, help="Text file with one code per line."
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        help="Output PDF file (default: <codes_file>.pdf).",
    )
    args = parser.parse_args()

    if not args.codes_file.is_file():
        print(f"Error: file not found: {args.codes_file}", file=sys.stderr)
        sys.exit(1)

    codes = load_codes(args.codes_file)
    if not codes:
        print("Error: no codes found in the input file.", file=sys.stderr)
        sys.exit(1)

    output_path = args.output or args.codes_file.with_suffix(".pdf")
    generate_pdf(codes, output_path)


if __name__ == "__main__":
    main()
