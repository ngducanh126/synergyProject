from flask import Blueprint, request, jsonify
from app import db, bcrypt
from flask_jwt_extended import create_access_token

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Check if the user already exists
    user_exists_query = "SELECT id FROM users WHERE username = :username"
    user_exists = db.session.execute(user_exists_query, {'username': username}).fetchone()

    if user_exists:
        return jsonify({'message': 'User already exists'}), 400

    # Hash the password and insert the new user
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    insert_query = """
        INSERT INTO users (username, password_hash)
        VALUES (:username, :password_hash)
    """
    db.session.execute(insert_query, {'username': username, 'password_hash': password_hash})
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Query to fetch the user by username
    user_query = "SELECT id, password_hash FROM users WHERE username = :username"
    user = db.session.execute(user_query, {'username': username}).fetchone()

    if user and bcrypt.check_password_hash(user['password_hash'], password):
        # Generate JWT access token
        access_token = create_access_token(identity=str(user['id']))
        return jsonify({'access_token': access_token}), 200

    return jsonify({'message': 'Invalid username or password'}), 401
