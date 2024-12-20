from flask import Blueprint, request, jsonify
from app import db
from app.models import User
from app.utils import hash_password, check_password
from app.auth import generate_token, login_required
from datetime import datetime

bp = Blueprint('routes', __name__)

# Register a new user
@bp.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    # Check if username exists
    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 400

    # Create a new user
    user = User(
        username=username,
        password_hash=hash_password(password),
        last_active=datetime.utcnow()
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201

# Login a user
@bp.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and check_password(user.password_hash, password):
        token = generate_token(user)
        user.last_active = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'Login successful', 'token': token}), 200

    return jsonify({'message': 'Invalid credentials'}), 401

# View user profile
@bp.route('/profile', methods=['GET'])
@login_required
def view_profile():
    user = request.user  # Retrieved from `login_required`
    return jsonify({
        'username': user.username,
        'bio': user.bio,
        'skills': user.skills,
        'location': user.location,
        'availability': user.availability,
        'last_active': user.last_active,
        'verification_status': user.verification_status
    }), 200

# Update user profile
@bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    user = request.user  # Retrieved from `login_required`
    data = request.json
    user.bio = data.get('bio', user.bio)
    user.skills = data.get('skills', user.skills)
    user.location = data.get('location', user.location)
    user.availability = data.get('availability', user.availability)
    user.last_active = datetime.utcnow()

    db.session.commit()
    return jsonify({'message': 'Profile updated successfully'}), 200

if __name__ == "__main__":
    import requests

    # Define base URL
    BASE_URL = "http://127.0.0.1:5000"

    # Test credentials
    USERNAME = "user8"
    PASSWORD = "hanoihue"

    # Login
    login_response = requests.post(f"{BASE_URL}/login", json={"username": USERNAME, "password": PASSWORD})

    if login_response.status_code == 200:
        print("Login Successful")
        token = login_response.json().get("token")
        print(f"Token: {token}")

        # Fetch Profile
        headers = {"Authorization": f"Bearer {token}"}
        profile_response = requests.get(f"{BASE_URL}/profile", headers=headers)

        if profile_response.status_code == 200:
            print("Profile Data:", profile_response.json())
        else:
            print("Failed to fetch profile", profile_response.status_code, profile_response.text)
    else:
        print("Login Failed", login_response.status_code, login_response.text)
