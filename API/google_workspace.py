import os

from googleapiclient.discovery import build


def get_workspace_service():
    """
    Placeholder for the real Google Workspace
    Admin SDK authentication.

    We will implement the approved authentication
    method once the credential approach is available.
    """

    raise NotImplementedError(
        "Google Workspace authentication is not configured yet."
    )


def user_exists(email):
    """
    Check whether a Google Workspace user exists.
    """

    # Temporary simulation
    existing_users = [
        "existing.user@example.com"
    ]

    return email in existing_users


def create_workspace_user(employee):

    email = employee.get("email")
    name = employee.get("name")

    print("\n==============================")
    print("GOOGLE WORKSPACE ONBOARDING")
    print("==============================")

    print(f"Name: {name}")
    print(f"Email: {email}")

    # --------------------------------
    # Validate email
    # --------------------------------

    if not email:

        return {
            "success": False,
            "email": None,
            "status": "missing_email"
        }

    # --------------------------------
    # Check duplicate
    # --------------------------------

    if user_exists(email):

        print("User already exists.")

        return {
            "success": False,
            "email": email,
            "status": "already_exists"
        }

    # --------------------------------
    # Temporary simulation
    # --------------------------------

    print("User creation simulated successfully.")

    return {
        "success": True,
        "email": email,
        "status": "simulated"
    }