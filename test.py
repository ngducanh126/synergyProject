import requests

# Base URL of the API
BASE_URL = "http://127.0.0.1:5000"

# Credentials
USERNAME = "user10"
PASSWORD = "hanoihue"

def login():
    """Logs in and returns the JWT token."""
    login_url = f"{BASE_URL}/login"
    login_data = {
        "username": USERNAME,
        "password": PASSWORD
    }

    print("Logging in...")
    login_response = requests.post(login_url, json=login_data)

    if login_response.status_code == 200:
        print("Login successful!")
        return login_response.json().get("token")
    else:
        print("Login failed:", login_response.status_code, login_response.text)
        return None

def update_profile(token):
    """Updates the profile with new information."""
    profile_url = f"{BASE_URL}/profile"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    profile_data = {
        "bio": "I am an artist passionate about collaborative projects.",
        "skills": ["Painting", "Sculpture", "Digital Art"],
        "location": "Hanoi, Vietnam",
        "availability": "Weekends"
    }

    print("Updating profile...")
    update_response = requests.put(profile_url, json=profile_data, headers=headers)

    if update_response.status_code == 200:
        print("Profile updated successfully!")
    else:
        print("Failed to update profile:", update_response.status_code, update_response.text)

def view_profile(token):
    """Fetches and displays the user's profile."""
    profile_url = f"{BASE_URL}/profile"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    print("Fetching profile...")
    profile_response = requests.get(profile_url, headers=headers)

    if profile_response.status_code == 200:
        print("Profile Data:")
        print(profile_response.json())
    else:
        print("Failed to fetch profile:", profile_response.status_code, profile_response.text)

if __name__ == "__main__":
    # Log in and get token
    token = login()

    if token:
        # Update profile
        update_profile(token)

        # View updated profile
        view_profile(token)
