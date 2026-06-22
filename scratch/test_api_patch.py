import requests

BASE_URL = 'http://127.0.0.1:8006/api'

# 1. Login
print("Logging in...")
login_res = requests.post(f"{BASE_URL}/auth/login/", json={
    'email': 'superadmin@yopmail.com',
    'password': 'demo1234'
})

print(f"Login status: {login_res.status_code}")
if login_res.status_code != 200:
    print(login_res.text)
    sys.exit(1)

login_data = login_res.json()
token = login_data['access']
headers = {
    'Authorization': f"Bearer {token}",
    'Content-Type': 'application/json'
}

# 2. Get current profile
get_res = requests.get(f"{BASE_URL}/auth/me/", headers=headers)
print(f"GET /auth/me/ status: {get_res.status_code}")
print("GET profile data:", get_res.json())

# 3. PATCH profile
patch_data = {
    'first_name': 'TestSuper',
    'last_name': 'TestAdmin',
    'email': 'superadmin@yopmail.com'
}
patch_res = requests.patch(f"{BASE_URL}/auth/me/", headers=headers, json=patch_data)
print(f"PATCH /auth/me/ status: {patch_res.status_code}")
print("PATCH profile response:", patch_res.text)

# 4. GET profile again to verify persistence
get_res2 = requests.get(f"{BASE_URL}/auth/me/", headers=headers)
print(f"GET /auth/me/ again status: {get_res2.status_code}")
print("GET profile data again:", get_res2.json())
