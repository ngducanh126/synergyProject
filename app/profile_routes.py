from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/view', methods=['GET'])
@jwt_required()
def view_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'message': 'User not found'}), 404

    user_data = {
        'id': user.id,
        'username': user.username,
        'bio': user.bio,
        'skills': user.skills,
        'location': user.location,
        'availability': user.availability,
        'verification_status': user.verification_status
    }
    return jsonify(user_data), 200

@profile_bp.route('/update', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'message': 'User not found'}), 404

    data = request.get_json()
    user.bio = data.get('bio', user.bio)
    user.skills = data.get('skills', user.skills)
    user.location = data.get('location', user.location)
    user.availability = data.get('availability', user.availability)

    db.session.commit()
    return jsonify({'message': 'Profile updated successfully'}), 200

@profile_bp.route('/add', methods=['POST'])
@jwt_required()
def add_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'message': 'User not found'}), 404

    # Prevent adding profile information if it already exists
    if user.bio or user.skills or user.location or user.availability:
        return jsonify({'message': 'Profile already exists. Use update endpoint to modify it.'}), 400

    data = request.get_json()
    user.bio = data.get('bio')
    user.skills = data.get('skills')
    user.location = data.get('location')
    user.availability = data.get('availability')

    db.session.commit()
    return jsonify({'message': 'Profile created successfully'}), 201
