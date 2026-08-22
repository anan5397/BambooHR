from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/admin.directory.user.readonly"
]

flow = InstalledAppFlow.from_client_secrets_file(
    "oauth_client.json",
    SCOPES
)

credentials = flow.run_local_server(port=0)

service = build(
    "admin",
    "directory_v1",
    credentials=credentials
)

result = service.users().list(
    customer="my_customer",
    maxResults=10
).execute()

for user in result.get("users", []):
    print(
        user.get("primaryEmail"),
        "|",
        user.get("name", {}).get("fullName")
    )