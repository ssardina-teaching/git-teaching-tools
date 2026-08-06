"""Get the worksheet of a Google Sheet

This is done using GSHEETS package: https://gsheets.readthedocs.io/en/stable/index.html

    this package provides an easier access to the Google Sheet API:

    https://developers.google.com/sheets/api/guides/concepts


    Google API: https://developers.google.com/drive/api/guides/about-sdk

Example to download the MARKING sheet from the Google Sheet with ID 16wc.....:

$ python git-hw-submissions.git/gg_get_worksheet.py 16wcDonn15ak88kCbOUGfyWimciD7zCSRLJdbVBP0uGs MARKING -c ~/.ssh/keys/credentials.json -o marking.csv


====================================================
Example of how to get a worksheet from a Google Sheet.
    https://developers.google.com/sheets/api/quickstart/python

Google API: https://developers.google.com/drive/api/guides/about-sdk

Python Client:
    https://github.com/googleapis/google-api-python-client
    https://developers.google.com/resources/api-libraries/documentation/sheets/v4/python/latest/index.html

Google Sheet API:
    https://developers.google.com/sheets/api/guides/concepts

    Set-up for Google Sheets: https://developers.google.com/sheets/api/quickstart/python

    In the end you should get a credentials.json

Google Google Workspace API: https://developers.google.com/drive/api/quickstart/python

    $ pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
"""
__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2024"

from argparse import ArgumentParser
from datetime import datetime
from gsheets import Sheets

from util import (
    TIMEZONE,
    UTC,
    NOW,
    NOW_ISO,
    NOW_TXT,
    LOGGING_DATE,
    LOGGING_FMT,
)


# setup my own logger for this script, using the slogger/loguru backend
from slogger.loguru_backend import logger, setup_logger

setup_logger(source=SCRIPT_NAME, timezone=TIMEZONE.key)


if __name__ == "__main__":
    parser = ArgumentParser(description="Merge PRs in multiple repos")
    parser.add_argument("SPREADSHEET", help="List of repositories to post comments to.")
    parser.add_argument("SHEET", help="List of student results.")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="output.csv",
        help="CSV output file %(default)s.",
    )
    parser.add_argument(
        "-c",
        "--credentials",
        default="credentials.json",
        help="File containing Google credentials %(default)s.",
    )
    parser.add_argument(
        "--webserver",
        action="store_true",
        help="Flag to enable webserver functionality for Google authentication (otherwise console-based).",
    )
    args = parser.parse_args()
    logger.info(f"Starting on {TIMEZONE}: {NOW_ISO} - {args}")

    spreadsheet_id = args.SPREADSHEET
    sheet_name = args.SHEET
    google_credentials = args.credentials
    csv_file = args.output

    # sheets = Sheets.from_files("~/client_secrets.json", "~/storage.json")
    gg_sheets = Sheets.from_files(
        google_credentials, "storage.json", no_webserver=not args.webserver
    )

    sheet = gg_sheets[spreadsheet_id].find(sheet_name)

    sheet.to_csv(csv_file, encoding="utf-8", dialect="excel")

    logger.info(f"Finished...")
