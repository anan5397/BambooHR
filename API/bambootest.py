import os
import requests

from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("BAMBOO_API_KEY")
subdomain = os.getenv("BAMBOO_SUBDOMAIN")

print("Subdomain:", subdomain)
print("API key loaded:", bool(api_key))

url = f"https://api.bamboohr.com/api/gateway.php/{subdomain}/v1/employees/directory"

response = requests.get(
    url,
    auth=(api_key, "x"),
    headers={
        "Accept": "application/json"
    }
)

print("Status:", response.status_code)
print("Response:", response.text[:500])