import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ["BAMBOO_API_KEY"]
subdomain = os.environ["BAMBOO_SUBDOMAIN"]

url = f"https://api.bamboohr.com/api/gateway.php/{subdomain}/v1/employees/directory"

response = requests.get(
    url,
    auth=(api_key, "x"),
    headers={
        "Accept": "application/json"
    }
)

print("Status:", response.status_code)
if response.status_code == 200:
    data = response.json()

    print("Number of employees:", len(data["employees"]))

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

    print(employees)

else:
    print(response.text)