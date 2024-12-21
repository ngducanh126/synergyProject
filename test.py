import requests

BASE_URL = "http://127.0.0.1:5000"

# Step 1: Register User
def register_user():
    url = f"{BASE_URL}/auth/register"
    payload = {
        "username": "user35",
        "password": "hanoihue"
    }
    response = requests.post(url, json=payload)
    print("Register Response:", response.json())
    return response.status_code == 201

# Step 2: Login User
def login_user():
    url = f"{BASE_URL}/auth/login"
    payload = {
        "username": "user30",
        "password": "hanoihue"
    }
    response = requests.post(url, json=payload)
    print("Login Response:", response.json())
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

# Step 3: Update Profile
def update_profile(token):
    url = f"{BASE_URL}/profile/update"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "bio": "Hello, I am user30!",
        "skills": ["painting", "drawing"],
        "location": "Hanoi, Vietnam",
        "availability": "Weekends"
    }
    response = requests.put(url, json=payload, headers=headers)
    print("Update Profile Response:", response.json())

# Main Flow
if __name__ == "__main__":
    if register_user():
        token = login_user()
        if token:
            update_profile(token)
        else:
            print("Login failed.")
    else:
        print("Registration failed.")
