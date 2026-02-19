import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_venues_error():
    # 1. Register/Login Admin
    auth_payload = {
        "email": "admin_debug@example.com",
        "password": "adminpassword",
        "full_name": "Admin Debug",
        "admin_secret": "change-this-admin-secret"
    }
    
    # Try register
    response = requests.post(f"{BASE_URL}/auth/admin/register", json=auth_payload)
    if response.status_code == 400:
        # Login if exists
        login_payload = {
            "username": auth_payload["email"],
            "password": auth_payload["password"]
        }
        response = requests.post(f"{BASE_URL}/auth/login", data=login_payload)

    if response.status_code not in [200, 201]:
        print(f"Auth failed: {response.text}")
        return

    token = response.json()["access_token"]
    print(f"Got admin token.")

    # 2. Fetch Venues (this should trigger the Enum error on read)
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/admin/venues", headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    test_venues_error()
