import os
import requests
import gspread

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from fastapi import FastAPI

#Testing
# =========================
# BAMBOOHR CONFIGURATION
# =========================

load_dotenv()

api_key = os.getenv("BAMBOO_API_KEY")
subdomain = os.getenv("BAMBOO_SUBDOMAIN")

if not api_key or not subdomain:
    raise ValueError("Missing BambooHR environment variables")


# =========================
# GOOGLE CONFIGURATION
# =========================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

client_secret = os.path.join(
    BASE_DIR,
    "client_secret.json"
)

token_file = os.path.join(
    BASE_DIR,
    "token.json"
)


# =========================
# GOOGLE AUTHENTICATION
# =========================

def get_google_credentials():

    credentials = None

    # Check if we already have saved credentials
    if os.path.exists(token_file):

        credentials = Credentials.from_authorized_user_file(
            token_file,
            SCOPES
        )

    # If credentials don't exist or are no longer valid
    if not credentials or not credentials.valid:

        if credentials and credentials.expired and credentials.refresh_token:

            credentials.refresh(Request())

        else:

            flow = InstalledAppFlow.from_client_secrets_file(
                client_secret,
                SCOPES
            )

            credentials = flow.run_local_server(port=0)

        # Save credentials for future runs
        with open(token_file, "w") as token:

            token.write(
                credentials.to_json()
            )

    return credentials


# =========================
# SYNC EMPLOYEES
# =========================

def sync_employees():

    # =========================
    # GET DATA FROM BAMBOOHR
    # =========================

    url = f"https://api.bamboohr.com/api/gateway.php/{subdomain}/v1/employees/directory"

    response = requests.get(
        url,
        auth=(api_key, "x"),
        headers={
            "Accept": "application/json"
        }
    )

    print("BambooHR Status:", response.status_code)

    if response.status_code != 200:
        raise Exception(
            f"BambooHR API error: {response.text}"
        )

    data = response.json()

    employees = []

    for employee in data["employees"]:

        employee_data = {
            "id": employee.get("id"),
            "name": employee.get("displayName"),
            "email": employee.get("workEmail"),
            "department": employee.get("department"),
            "job_title": employee.get("jobTitle")
        }

        employees.append(employee_data)

    print(f"Retrieved {len(employees)} employees")


    # =========================
    # GOOGLE SHEETS
    # =========================

    credentials = get_google_credentials()

    client = gspread.authorize(credentials)

    spreadsheet = client.open("BambooHR_sheet")

    worksheet = spreadsheet.sheet1


    # =========================
    # WRITE HEADERS
    # =========================

    worksheet.update(
        "A1:E1",
        [[
            "ID",
            "Name",
            "Email",
            "Department",
            "Job Title"
        ]]
    )


    # =========================
    # CONVERT EMPLOYEES TO ROWS
    # =========================

    rows = []

    for employee in employees:

        rows.append([
            employee["id"],
            employee["name"],
            employee["email"],
            employee["department"],
            employee["job_title"]
        ])


    # =========================
    # WRITE EMPLOYEES
    # =========================

    if rows:

        worksheet.update(
            f"A2:E{len(rows) + 1}",
            rows
        )

    print(
        "Successfully synced BambooHR employees to Google Sheets!"
    )

    return {
        "success": True,
        "employees_synced": len(employees)
    }


# =========================
# FASTAPI
# =========================

app = FastAPI()


@app.post("/sync-employees")
def sync():

    return sync_employees()

if __name__ == "__main__":
    result = sync_employees()
    print(result)