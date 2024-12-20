import jwt
from flask import request, jsonify
from functools import wraps
from datetime import datetime, timedelta
from app.models import User
from app import db
from app.config import Config

def generate_token(user):
    """
    Generate a JWT token for the given user.
    """
    payload = {
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(days=7),  # Token valid for 7 days
        'iat': datetime.utcnow()  # Issued at
    }
    token = jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')
    return token

def verify_token(token):
    """
    Decode and verify the JWT token.
    """
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def login_required(f):
    """
    Decorator to protect endpoints with authentication.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        token = token.split("Bearer ")[-1]  # Strip "Bearer " prefix
        user_id = verify_token(token)
        if not user_id:
            return jsonify({'message': 'Invalid or expired token!'}), 401
        
        # Attach the user to the request object for downstream use
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found!'}), 404

        request.user = user
        return f(*args, **kwargs)
    return decorated_function
