import os
import secrets
import string

# Used to authenticate using our Google Cloud Service Account
from google.oauth2 import service_account

# Used to create a connection to the Google Admin SDK
from googleapiclient.discovery import build

# Lets us handle Google API errors such as 404, 403, etc.
from googleapiclient.errors import HttpError


# ============================================================
# GOOGLE WORKSPACE CONFIGURATION
# ============================================================

# This is the permission our service account needs.
#
# admin.directory.user allows us to:
# - Check whether Workspace users exist
# - Create users
# - Update users
# - Delete/suspend users
#
# We already authorized this exact scope in:
#
# Google Admin Console
# → Security
# → API Controls
# → Domain-Wide Delegation
#
SCOPES = [
    "https://www.googleapis.com/auth/admin.directory.user"
]


# This should contain YOUR Google Workspace administrator email.
#
# Example:
# GOOGLE_ADMIN_EMAIL=admin@anantest.org
#
# This is NOT the service account email.
#
# We need this because the service account will impersonate
# this administrator when making Google Workspace requests.
GOOGLE_ADMIN_EMAIL = os.getenv("GOOGLE_ADMIN_EMAIL")


# ============================================================
# FIND SERVICE ACCOUNT CREDENTIAL FILE
# ============================================================

def get_service_account_path():
    """
    Find the service_account.json file.

    Render and our local computer store this file
    in different locations.
    """

    # Render automatically makes Secret Files available inside:
    #
    # /etc/secrets/
    #
    # So our Render Secret File:
    #
    # service_account.json
    #
    # becomes:
    #
    # /etc/secrets/service_account.json
    if os.getenv("RENDER"):

        return "/etc/secrets/service_account.json"

    # When running locally, look for service_account.json
    # inside the same folder as google_workspace.py.
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "service_account.json"
    )


# ============================================================
# CONNECT TO GOOGLE WORKSPACE ADMIN SDK
# ============================================================

def get_workspace_service():
    """
    Authenticate our backend with Google Workspace.

    Authentication flow:

    service_account.json
            ↓
    Authenticate as Google Cloud Service Account
            ↓
    Domain-Wide Delegation
            ↓
    Impersonate GOOGLE_ADMIN_EMAIL
            ↓
    Google Admin SDK
    """

    # Make sure we actually configured an administrator.
    #
    # Without this, the service account wouldn't know
    # which Workspace administrator it should impersonate.
    if not GOOGLE_ADMIN_EMAIL:

        raise ValueError(
            "GOOGLE_ADMIN_EMAIL environment variable is missing."
        )


    # --------------------------------------------------------
    # STEP 1: Authenticate the Service Account
    # --------------------------------------------------------

    # service_account.json contains the service account's
    # identity and private key.
    #
    # This proves to Google:
    #
    # "I really am this service account."
    credentials = (
        service_account.Credentials.from_service_account_file(

            get_service_account_path(),

            # Only request the permissions that we need.
            scopes=SCOPES
        )
    )


    # --------------------------------------------------------
    # STEP 2: Impersonate the Workspace administrator
    # --------------------------------------------------------

    # A service account by itself is NOT a normal
    # Google Workspace employee/admin.
    #
    # Domain-Wide Delegation allows this service account
    # to act ON BEHALF OF a Workspace user.
    #
    # Here we tell Google:
    #
    # "Use these service-account credentials,
    # but perform the request as GOOGLE_ADMIN_EMAIL."
    delegated_credentials = credentials.with_subject(
        GOOGLE_ADMIN_EMAIL
    )


    # --------------------------------------------------------
    # STEP 3: Connect to Google Admin SDK
    # --------------------------------------------------------

    # "admin" = Google Admin SDK
    # "directory_v1" = Directory API version
    #
    # The Directory API is what lets us manage things like:
    #
    # users
    # groups
    # organizational units
    # etc.
    service = build(
        "admin",
        "directory_v1",
        credentials=delegated_credentials
    )

    return service


# ============================================================
# CHECK IF A GOOGLE WORKSPACE USER ALREADY EXISTS
# ============================================================

def user_exists(email):
    """
    Check Google Workspace for an existing account.

    This prevents us from accidentally trying to create
    the same employee twice.
    """

    # Authenticate and connect to Admin SDK.
    service = get_workspace_service()

    try:

        # Ask Google:
        #
        # "Is there a Workspace user with this email?"
        service.users().get(
            userKey=email
        ).execute()

        # If Google successfully returns the user,
        # the account already exists.
        return True


    except HttpError as error:

        # HTTP 404 means:
        #
        # User Not Found
        #
        # In our case that's actually good because it means
        # we're allowed to continue creating the employee.
        if error.resp.status == 404:

            return False

        # Something else happened:
        #
        # 403 → permission problem
        # 401 → authentication problem
        # etc.
        #
        # Don't pretend the employee doesn't exist.
        # Pass the error upward so we can investigate it.
        raise


# ============================================================
# GENERATE TEMPORARY PASSWORD
# ============================================================

def generate_temporary_password(length=16):
    """
    Generate a random temporary password for the new employee.
    """

    # Characters that can appear in the password.
    alphabet = (
        string.ascii_letters
        + string.digits
        + "!@#$%&*"
    )

    # secrets is designed for security-sensitive randomness.
    #
    # We use secrets instead of Python's normal random module
    # because this value is a password.
    return "".join(
        secrets.choice(alphabet)
        for _ in range(length)
    )


# ============================================================
# CREATE GOOGLE WORKSPACE USER
# ============================================================

def create_workspace_user(employee):
    """
    Create a real Google Workspace account from
    a BambooHR employee.

    Expected employee data:

    {
        "id": "4",
        "name": "Charlotte Abbott",
        "email": "cabbott@example.com",
        ...
    }
    """

    # Pull the information we need from BambooHR data.
    email = employee.get("email")
    name = employee.get("name")


    print("\n==============================")
    print("GOOGLE WORKSPACE ONBOARDING")
    print("==============================")

    print(f"Name: {name}")
    print(f"Email: {email}")


    # ========================================================
    # 1. VALIDATE EMPLOYEE DATA
    # ========================================================

    # We cannot create a Workspace account without an email.
    if not email:

        return {
            "success": False,
            "email": None,
            "status": "missing_email"
        }


    # We also want a name because Google Workspace
    # requires givenName and familyName.
    if not name:

        return {
            "success": False,
            "email": email,
            "status": "missing_name"
        }


    # ========================================================
    # 2. CHECK FOR DUPLICATES
    # ========================================================

    # Before creating anything, ask Google Workspace
    # whether this email already exists.
    if user_exists(email):

        print("User already exists.")

        return {
            "success": False,
            "email": email,
            "status": "already_exists"
        }


    # ========================================================
    # 3. SPLIT EMPLOYEE NAME
    # ========================================================

    # Example:
    #
    # "Charlotte Abbott"
    #
    # becomes:
    #
    # ["Charlotte", "Abbott"]
    name_parts = name.strip().split()


    # First word becomes given name.
    first_name = name_parts[0]


    # Everything after the first word becomes family name.
    #
    # This also handles names with multiple words better than
    # simply assuming there are exactly two words.
    if len(name_parts) > 1:

        last_name = " ".join(
            name_parts[1:]
        )

    else:

        # Google expects a family name, so provide a fallback.
        last_name = "Employee"


    # ========================================================
    # 4. GENERATE TEMPORARY PASSWORD
    # ========================================================

    temporary_password = generate_temporary_password()


    # ========================================================
    # 5. BUILD GOOGLE WORKSPACE USER
    # ========================================================

    # This dictionary becomes the JSON request body sent
    # to Google's Directory API.
    user_body = {

        # Employee's new Google Workspace login.
        "primaryEmail": email,

        "name": {

            "givenName": first_name,

            "familyName": last_name
        },

        # Initial password for the account.
        "password": temporary_password,

        # Force the employee to choose their own password
        # after their first login.
        "changePasswordAtNextLogin": True
    }


    # ========================================================
    # 6. CONNECT TO GOOGLE ADMIN SDK
    # ========================================================

    service = get_workspace_service()


    # ========================================================
    # 7. CREATE THE USER
    # ========================================================

    try:

        # This is the actual Google Workspace API request.
        #
        # Before this line executes:
        #     Nothing has been created.
        #
        # When .execute() succeeds:
        #     A REAL Google Workspace user now exists.
        created_user = (
            service
            .users()
            .insert(body=user_body)
            .execute()
        )


        print(
            "Google Workspace user created:",
            created_user["primaryEmail"]
        )


        # Tell combined.py that onboarding succeeded.
        return {

            "success": True,

            "email": created_user["primaryEmail"],

            "status": "created"
        }


    # ========================================================
    # 8. HANDLE GOOGLE API ERRORS
    # ========================================================

    except HttpError as error:

        print(
            "Google Workspace API error:",
            error
        )


        return {

            "success": False,

            "email": email,

            "status": "google_api_error",

            "error": str(error)
        }