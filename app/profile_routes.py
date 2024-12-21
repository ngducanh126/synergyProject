from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/view', methods=['GET'])
@jwt_required()
def view_profile():
    user_id = get_jwt_identity()

    # Fetch user details
    query = """
    SELECT id, username, bio, skills, location, availability, verification_status
    FROM users
    WHERE id = :user_id;
    """
    user = db.session.execute(query, {'user_id': user_id}).fetchone()

    if not user:
        return jsonify({'message': 'User not found'}), 404

    user_data = {
        'id': user[0],
        'username': user[1],
        'bio': user[2],
        'skills': user[3],
        'location': user[4],
        'availability': user[5],
        'verification_status': user[6],
    }
    return jsonify(user_data), 200


@profile_bp.route('/update', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()

    # Check if the user exists
    user_query = "SELECT id FROM users WHERE id = :user_id;"
    user = db.session.execute(user_query, {'user_id': user_id}).fetchone()

    if not user:
        return jsonify({'message': 'User not found'}), 404

    # Update profile data
    data = request.get_json()
    update_query = """
    UPDATE users
    SET bio = COALESCE(:bio, bio),
        skills = COALESCE(:skills, skills),
        location = COALESCE(:location, location),
        availability = COALESCE(:availability, availability)
    WHERE id = :user_id;
    """
    db.session.execute(
        update_query,
        {
            'bio': data.get('bio'),
            'skills': data.get('skills'),
            'location': data.get('location'),
            'availability': data.get('availability'),
            'user_id': user_id,
        },
    )
    db.session.commit()
    return jsonify({'message': 'Profile updated successfully'}), 200


@profile_bp.route('/add', methods=['POST'])
@jwt_required()
def add_profile():
    user_id = get_jwt_identity()

    # Check if the user exists and already has profile data
    user_query = """
    SELECT bio, skills, location, availability
    FROM users
    WHERE id = :user_id;
    """
    user = db.session.execute(user_query, {'user_id': user_id}).fetchone()

    if not user:
        return jsonify({'message': 'User not found'}), 404

    # Prevent adding profile information if it already exists
    if user[0] or user[1] or user[2] or user[3]:
        return jsonify({'message': 'Profile already exists. Use update endpoint to modify it.'}), 400

    # Add new profile data
    data = request.get_json()
    insert_query = """
    UPDATE users
    SET bio = :bio,
        skills = :skills,
        location = :location,
        availability = :availability
    WHERE id = :user_id;
    """
    db.session.execute(
        insert_query,
        {
            'bio': data.get('bio'),
            'skills': data.get('skills'),
            'location': data.get('location'),
            'availability': data.get('availability'),
            'user_id': user_id,
        },
    )
    db.session.commit()
    return jsonify({'message': 'Profile created successfully'}), 201
