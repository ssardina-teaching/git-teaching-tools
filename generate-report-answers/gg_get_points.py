import gspread
from google.oauth2.service_account import Credentials

# ---- CONFIGURE THESE ----
SERVICE_ACCOUNT_FILE = "service_account.json"
SPREADSHEET_ID = "1SttMV-U3dAJAOEeEp-cgFvv_v_qL4qIEG35x9Ni93l0"
RESPONSE_SHEET_NAME = "FEC-AI25"    # default Google Forms link
# -------------------------

# Authorize
scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
gc = gspread.authorize(creds)

# Open response sheet
sheet = gc.open_by_key(SPREADSHEET_ID).worksheet(RESPONSE_SHEET_NAME)

# Read everything
data = sheet.get_all_records()

# Identify question columns and score columns
# Typical structure:
#   Timestamp | Email | Q1 | Q2 | ... | Score | ...
# Quiz scoring generates extra columns named like "Q1 - Points" or similar

columns = sheet.row_values(1)

question_cols = []
points_cols = []

for col in columns:
    if "Points" in col or "Score" in col:
        points_cols.append(col)
    elif col not in ("Timestamp", "Email"):
        question_cols.append(col)

print("Detected questions:", question_cols)
print("Detected points columns:", points_cols)

# Build per-submission mark table
results = []

for row in data:
    entry = {
        "Timestamp": row.get("Timestamp"),
        "Email": row.get("Email", None),
    }
    for col in points_cols:
        entry[col] = row.get(col)
    results.append(entry)

# Print results
for r in results:
    print(r)
