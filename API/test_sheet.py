import os
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

client_secret = os.path.join(
    BASE_DIR,
    "client_secret.json"
)

flow = InstalledAppFlow.from_client_secrets_file(
    client_secret,
    SCOPES
)

credentials = flow.run_local_server(port=0)

client = gspread.authorize(credentials)

spreadsheet = client.open("BambooHR_sheet")
worksheet = spreadsheet.sheet1

worksheet.update("A2", [["LETS"]])

print("Successfully wrote to Google Sheets!")