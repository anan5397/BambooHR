import os
import requests

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# ==========================================
# 1. Get employees from BambooHR
# ==========================================

api_key = os.environ["BAMBOO_API_KEY"]
subdomain = os.environ["BAMBOO_SUBDOMAIN"]

bamboo_url = (
    f"https://api.bamboohr.com/api/gateway.php/"
    f"{subdomain}/v1/employees/directory"
)

print("Bamboo URL:", bamboo_url)

response = requests.get(
    bamboo_url,
    auth=(api_key, "x"),
    headers={"Accept": "application/json"}
)

if response.status_code != 200:
    print("BambooHR error:", response.status_code)
    print(response.text)
    exit()

bamboo_data = response.json()

bamboo_emails = set()

for employee in bamboo_data["employees"]:
    email = employee.get("workEmail")

    if email:
        bamboo_emails.add(email.lower())


# ==========================================
# 2. Get users from Google Workspace
# ==========================================

SCOPES = [
    "https://www.googleapis.com/auth/admin.directory.user.readonly"
]

flow = InstalledAppFlow.from_client_secrets_file(
    "oauth_client.json",
    SCOPES
)

credentials = flow.run_local_server(port=0)

google_service = build(
    "admin",
    "directory_v1",
    credentials=credentials
)

google_emails = set()

page_token = None

while True:

    result = google_service.users().list(
        customer="my_customer",
        maxResults=100,
        pageToken=page_token
    ).execute()

    for user in result.get("users", []):
        email = user.get("primaryEmail")

        if email:
            google_emails.add(email.lower())

    page_token = result.get("nextPageToken")

    if not page_token:
        break


# ==========================================
# 3. Compare the systems
# ==========================================

missing_from_google = bamboo_emails - google_emails


print("\n==============================")
print("BambooHR employees:", len(bamboo_emails))
print("Google Workspace users:", len(google_emails))
print("==============================\n")


if missing_from_google:

    print("Employees in BambooHR but NOT in Google Workspace:")

    for email in sorted(missing_from_google):
        print("  →", email)

else:

    print("All BambooHR employees have Google Workspace accounts.")