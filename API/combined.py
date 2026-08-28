import os
from datetime import datetime

import requests
import gspread

from dotenv import load_dotenv

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from fastapi import FastAPI, HTTPException

from google_workspace import create_workspace_user


# ============================================================
# ENVIRONMENT CONFIGURATION
# ============================================================

load_dotenv()

api_key = os.getenv("BAMBOO_API_KEY")
subdomain = os.getenv("BAMBOO_SUBDOMAIN")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
print("================================")
print("COMBINED.PY LOADED")
print("BAMBOO SUBDOMAIN:", subdomain)
print("BAMBOO API KEY LOADED:", bool(api_key))
print("================================")
if not api_key or not subdomain:
    raise ValueError(
        "Missing BambooHR environment variables"
    )

print("BambooHR subdomain:", subdomain)
print("BambooHR API key loaded:", bool(api_key))

# ============================================================
# GOOGLE CONFIGURATION
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# GOOGLE CREDENTIAL FILES
# ============================================================

if os.getenv("RENDER"):

    client_secret = "/etc/secrets/client_secret.json"
    token_file = "/etc/secrets/token.json"

else:

    client_secret = os.path.join(
        BASE_DIR,
        "client_secret.json"
    )

    token_file = os.path.join(
        BASE_DIR,
        "token.json"
    )


# ============================================================
# GOOGLE AUTHENTICATION
# ============================================================

def get_google_credentials():

    credentials = None

    # --------------------------------
    # Load existing token
    # --------------------------------

    if os.path.exists(token_file):

        credentials = Credentials.from_authorized_user_file(
            token_file,
            SCOPES
        )

    # --------------------------------
    # Check credentials
    # --------------------------------

    if not credentials or not credentials.valid:

        # Refresh expired credentials
        if (
            credentials
            and credentials.expired
            and credentials.refresh_token
        ):

            credentials.refresh(
                Request()
            )

        # First-time authentication
        else:

            flow = InstalledAppFlow.from_client_secrets_file(
                client_secret,
                SCOPES
            )

            credentials = flow.run_local_server(
                port=0
            )

        # --------------------------------
        # Save token locally
        # --------------------------------

        if not os.getenv("RENDER"):

            with open(
                token_file,
                "w"
            ) as token:

                token.write(
                    credentials.to_json()
                )

    return credentials


# ============================================================
# BAMBOOHR — GET ALL EMPLOYEES
# ============================================================

def get_all_employees():

    url = (
    f"https://{subdomain}.bamboohr.com/"
    f"api/v1/employees/directory"
)

    print("BambooHR URL:", url)

    response = requests.get(
         url,
        auth=(api_key, "x"),
        headers={
        "Accept": "application/json"
    }
)

    print("BambooHR Status:", response.status_code)
    print("BambooHR Response:", repr(response.text))



    if response.status_code != 200:

        raise Exception(
            f"BambooHR API error: {response.text}"
        )

    data = response.json()

    employees = []

    for employee in data["employees"]:

        employee_data = {

            "id": employee.get("id"),

            "name": employee.get(
                "displayName"
            ),

            "email": employee.get(
                "workEmail"
            ),

            "department": employee.get(
                "department"
            ),

            "job_title": employee.get(
                "jobTitle"
            )
        }

        employees.append(
            employee_data
        )

    print(
        f"Retrieved {len(employees)} employees"
    )

    return employees


# ============================================================
# BAMBOOHR — GET ONE EMPLOYEE
# ============================================================

def get_employee(employee_id):

    employees = get_all_employees()

    for employee in employees:

        if str(employee["id"]) == str(employee_id):

            return employee

    raise Exception(
        f"Employee {employee_id} not found"
    )


# ============================================================
# GOOGLE SHEETS — SYNC EMPLOYEES
# ============================================================

def sync_employees():

    employees = get_all_employees()

    # --------------------------------
    # Google authentication
    # --------------------------------

    credentials = get_google_credentials()

    client = gspread.authorize(
        credentials
    )

    # --------------------------------
    # Open spreadsheet
    # --------------------------------
    print("GOOGLE SHEET ID:", GOOGLE_SHEET_ID)

    spreadsheet = client.open_by_key(
    GOOGLE_SHEET_ID
)   #THIS RIGHT HEREEEEEEEEEEEEEEEEEEE
    worksheet = spreadsheet.sheet1

    # --------------------------------
    # Headers
    # --------------------------------

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

    # --------------------------------
    # Convert employees to rows
    # --------------------------------

    rows = []

    for employee in employees:

        rows.append([
            employee["id"],
            employee["name"],
            employee["email"],
            employee["department"],
            employee["job_title"]
        ])

    # --------------------------------
    # Write employees
    # --------------------------------

    if rows:

        worksheet.update(
            f"A2:E{len(rows) + 1}",
            rows
        )

    print(
        "Successfully synced BambooHR employees "
        "to Google Sheets!"
    )

    return {

        "success": True,

        "employees_synced": len(
            employees
        )
    }


# ============================================================
# GOOGLE SHEETS — ONBOARDING LOG
# ============================================================

def log_onboarding(
    employee,
    result
):

    # --------------------------------
    # Authenticate
    # --------------------------------

    credentials = get_google_credentials()

    client = gspread.authorize(
        credentials
    )

    # --------------------------------
    # Open spreadsheet
    # --------------------------------

    spreadsheet = client.open_by_key(
    GOOGLE_SHEET_ID
)

    worksheet = spreadsheet.worksheet(
        "Onboarding Log"
    )
    print("GOOGLE SHEET ID:", GOOGLE_SHEET_ID)
    # --------------------------------
    # Add audit record
    # --------------------------------

    worksheet.append_row([

        employee.get("id"),

        employee.get("name"),

        employee.get("email"),

        employee.get("department"),

        employee.get("job_title"),

        "Create Google Workspace User",

        result.get("status"),

        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    ])

    return True


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="BambooHR Onboarding API",
    description="Employee onboarding automation API",
    version="1.0"
)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def health_check():

    return {
        "status": "online",
        "service": "BambooHR Onboarding API"
    }


# ============================================================
# SYNC EMPLOYEES
# ============================================================

@app.post("/sync-employees")
def sync():

    try:

        return sync_employees()

    except requests.exceptions.RequestException as e:

        raise HTTPException(
            status_code=502,
            detail=f"BambooHR connection failed: {str(e)}"
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Employee synchronization failed: {str(e)}"
        )

# ============================================================
# ONBOARD EMPLOYEE
# ============================================================
@app.post("/onboard/{employee_id}")
def onboard_employee(employee_id: str):

    # ========================================================
    # GET EMPLOYEE
    # ========================================================

    try:

        employee = get_employee(employee_id)

    except Exception as e:

        raise HTTPException(
            status_code=404,
            detail=str(e)
        )


    # ========================================================
    # VALIDATE EMPLOYEE
    # ========================================================

    if not employee.get("email"):

        raise HTTPException(
            status_code=400,
            detail=(
                f"Employee {employee_id} "
                "does not have a work email."
            )
        )


    # ========================================================
    # CREATE GOOGLE WORKSPACE USER
    # ========================================================

    try:

        onboarding_result = create_workspace_user(
            employee
        )

    except Exception as e:

        raise HTTPException(
            status_code=502,
            detail=(
                "Google Workspace onboarding failed: "
                f"{str(e)}"
            )
        )


    # ========================================================
    # LOG ONBOARDING
    # ========================================================

    try:

        log_onboarding(
            employee,
            onboarding_result
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "User onboarding succeeded, "
                "but audit logging failed: "
                f"{str(e)}"
            )
        )


    # ========================================================
    # RETURN RESULT
    # ========================================================

    return {

        "success": True,

        "employee": employee,

        "workspace_result": onboarding_result
    }

# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":

    result = sync_employees()

    print(result)