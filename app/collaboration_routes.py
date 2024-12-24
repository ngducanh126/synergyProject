from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
from app import db


collaboration_bp = Blueprint('collaboration', __name__)

# Create a collaboration
@collaboration_bp.route('/create', methods=['POST'])
@jwt_required()
def create_collaboration():
    user_id = get_jwt_identity()
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')

    if not name:
        return jsonify({'error': 'Collaboration name is required'}), 400

    try:
        # Insert the collaboration into the database
        query = """
        INSERT INTO collaborations (admin_id, name, description)
        VALUES (:admin_id, :name, :description)
        RETURNING id;
        """
        result = db.session.execute(query, {'admin_id': user_id, 'name': name, 'description': description})
        collaboration_id = result.fetchone()[0]

        # Add the creator as an admin to the user_collaborations table
        user_collab_query = """
        INSERT INTO user_collaborations (user_id, collaboration_id, role)
        VALUES (:user_id, :collaboration_id, 'admin');
        """
        db.session.execute(user_collab_query, {'user_id': user_id, 'collaboration_id': collaboration_id})
        db.session.commit()

        return jsonify({'message': 'Collaboration created successfully', 'id': collaboration_id}), 201
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to create collaboration'}), 500


# Add photo to a collaboration
@collaboration_bp.route('/<int:collaboration_id>/photos', methods=['POST'])
@jwt_required()
def add_photo_to_collaboration(collaboration_id):
    user_id = get_jwt_identity()

    # Check if the user is an admin of the collaboration
    admin_query = """
    SELECT role FROM user_collaborations
    WHERE user_id = :user_id AND collaboration_id = :collaboration_id AND role = 'admin';
    """
    admin = db.session.execute(admin_query, {'user_id': user_id, 'collaboration_id': collaboration_id}).fetchone()

    if not admin:
        return jsonify({'error': 'You do not have permission to add photos to this collaboration'}), 403

    # Check if the request contains a file
    if 'file' not in request.files:
        return jsonify({'error': 'Photo file is required'}), 400

    file = request.files['file']
    filename = secure_filename(file.filename)
    file_path = os.path.join('uploads', filename)
    file.save(file_path)

    # Add photo to the collaboration_photos table
    try:
        query = """
        INSERT INTO collaboration_photos (collaboration_id, photo_path)
        VALUES (:collaboration_id, :photo_path);
        """
        db.session.execute(query, {'collaboration_id': collaboration_id, 'photo_path': file_path})
        db.session.commit()

        return jsonify({'message': 'Photo added successfully', 'file_path': file_path}), 201
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to add photo'}), 500


# View all collaborations
@collaboration_bp.route('/view', methods=['GET'])
@jwt_required()
def view_collaborations():
    try:
        user_id = get_jwt_identity()
        print(f"[DEBUG] Token validated. User ID: {user_id}")

        # Query to fetch all collaborations
        query = """
        SELECT c.id, c.name, c.description, c.created_at, u.username AS admin_name
        FROM collaborations c
        JOIN users u ON c.admin_id = u.id;
        """
        collaborations = db.session.execute(query).fetchall()

        collaborations_data = [
            {
                'id': collab[0],
                'name': collab[1],
                'description': collab[2],
                'created_at': collab[3].isoformat(),
                'admin_name': collab[4],
            }
            for collab in collaborations
        ]

        print(f"[DEBUG] Retrieved {len(collaborations_data)} collaborations.")
        return jsonify(collaborations_data), 200
    except Exception as e:
        print(f"[ERROR] Failed to fetch collaborations: {e}")
        return jsonify({'error': 'Failed to fetch collaborations'}), 500





# View photos in a collaboration
@collaboration_bp.route('/<int:collaboration_id>/photos', methods=['GET'])
@jwt_required()
def view_collaboration_photos(collaboration_id):
    try:
        query = """
        SELECT id, photo_path FROM collaboration_photos
        WHERE collaboration_id = :collaboration_id;
        """
        photos = db.session.execute(query, {'collaboration_id': collaboration_id}).fetchall()

        photos_data = [
            {
                'id': photo[0],
                'photo_url': f"http://127.0.0.1:5000/uploads/{os.path.basename(photo[1])}"
            }
            for photo in photos
        ]
        return jsonify(photos_data), 200
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to fetch photos'}), 500


@collaboration_bp.route('/my', methods=['GET'])
@jwt_required()
def view_my_collaborations():
    user_id = get_jwt_identity()
    try:
        print(f"[DEBUG] Fetching collaborations for user_id: {user_id}")

        # Query to fetch collaborations where the user is the admin
        query = """
        SELECT id, name, description, created_at
        FROM collaborations
        WHERE admin_id = :user_id;
        """
        my_collaborations = db.session.execute(query, {'user_id': user_id}).fetchall()

        collaborations_data = [
            {
                'id': collab[0],
                'name': collab[1],
                'description': collab[2],
                'created_at': collab[3].isoformat(),
            }
            for collab in my_collaborations
        ]

        print(f"[DEBUG] User {user_id} is admin of {len(collaborations_data)} collaborations.")
        return jsonify(collaborations_data), 200
    except Exception as e:
        print(f"[ERROR] Failed to fetch user's collaborations: {e}")
        return jsonify({'error': 'Failed to fetch collaborations'}), 500



@collaboration_bp.route('/<int:collaboration_id>', methods=['GET'])
@jwt_required()
def view_collaboration(collaboration_id):
    query = """
    SELECT c.id, c.name, c.description, u.username AS admin_name
    FROM collaborations c
    JOIN users u ON c.admin_id = u.id
    WHERE c.id = :collaboration_id;
    """
    collab = db.session.execute(query, {'collaboration_id': collaboration_id}).fetchone()

    if not collab:
        return jsonify({'error': 'Collaboration not found'}), 404

    collaboration_data = {
        'id': collab[0],
        'name': collab[1],
        'description': collab[2],
        'admin_name': collab[3]
    }
    return jsonify(collaboration_data), 200
