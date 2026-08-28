from googleapiclient.discovery import build

print("Admin SDK library loaded successfully")

service = build(
    "admin",
    "directory_v1"
)

print("Admin SDK service created successfully")