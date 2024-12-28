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

@collaboration_bp.route('/<int:collaboration_id>/request', methods=['POST'])
@jwt_required()
def request_to_join_collaboration(collaboration_id):
    user_id = get_jwt_identity()
    try:
        # Check if the user has an existing pending request
        existing_request_query = """
        SELECT id FROM collaboration_requests
        WHERE user_id = :user_id AND collaboration_id = :collaboration_id AND status = 'pending';
        """
        existing_request = db.session.execute(
            existing_request_query, {'user_id': user_id, 'collaboration_id': collaboration_id}
        ).fetchone()

        if existing_request:
            return jsonify({'error': 'You already have a pending request to this collaboration.'}), 400

        # Insert the new request
        insert_query = """
        INSERT INTO collaboration_requests (user_id, collaboration_id, status)
        VALUES (:user_id, :collaboration_id, 'pending');
        """
        db.session.execute(insert_query, {'user_id': user_id, 'collaboration_id': collaboration_id})
        db.session.commit()

        return jsonify({'message': 'Request sent successfully.'}), 201
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to send request.'}), 500


@collaboration_bp.route('/my-requests', methods=['GET'])
@jwt_required()
def view_my_collab_requests():
    user_id = get_jwt_identity()
    try:
        query = """
        SELECT cr.id, cr.status, c.name AS collaboration_name, c.description, cr.created_at
        FROM collaboration_requests cr
        JOIN collaborations c ON cr.collaboration_id = c.id
        WHERE cr.user_id = :user_id;
        """
        requests = db.session.execute(query, {'user_id': user_id}).fetchall()

        requests_data = [
            {
                'id': req[0],
                'status': req[1],
                'collaboration_name': req[2],
                'collaboration_description': req[3],
                'date': req[4].strftime('%Y-%m-%d %H:%M:%S') if req[4] else None,
            }
            for req in requests
        ]
        return jsonify(requests_data), 200
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to fetch collaboration requests.'}), 500



@collaboration_bp.route('/requests/<int:request_id>', methods=['PUT'])
@jwt_required()
def handle_collaboration_request(request_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    status = data.get('status')  # 'approved' or 'rejected'

    if status not in ['approved', 'rejected']:
        return jsonify({'error': 'Invalid status. Use "approved" or "rejected".'}), 400

    try:
        # Update the request status
        update_query = """
        UPDATE collaboration_requests
        SET status = :status
        WHERE id = :request_id;
        """
        db.session.execute(update_query, {'status': status, 'request_id': request_id})
        db.session.commit()

        # If approved, add the user to the collaboration
        if status == 'approved':
            user_collab_query = """
            INSERT INTO user_collaborations (user_id, collaboration_id, role)
            SELECT cr.user_id, cr.collaboration_id, 'member'
            FROM collaboration_requests cr
            WHERE cr.id = :request_id;
            """
            db.session.execute(user_collab_query, {'request_id': request_id})
            db.session.commit()

        return jsonify({'message': f'Request has been {status} successfully.'}), 200
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to handle collaboration request.'}), 500



@collaboration_bp.route('/admin-requests', methods=['GET'])
@jwt_required()
def view_pending_requests_for_admin():
    user_id = get_jwt_identity()
    try:
        query = """
        SELECT cr.id, cr.status, u.username AS requester_name, c.name AS collaboration_name
        FROM collaboration_requests cr
        JOIN collaborations c ON cr.collaboration_id = c.id
        JOIN users u ON cr.user_id = u.id
        WHERE c.admin_id = :user_id AND cr.status = 'pending';
        """
        requests = db.session.execute(query, {'user_id': user_id}).fetchall()

        requests_data = [
            {
                'id': req[0],
                'status': req[1],
                'requester_name': req[2],
                'collaboration_name': req[3],
            }
            for req in requests
        ]
        return jsonify(requests_data), 200
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to fetch pending requests.'}), 500

@collaboration_bp.route('/joined', methods=['GET'])
@jwt_required()
def view_collaborations_i_joined():
    user_id = get_jwt_identity()
    try:
        query = """
        SELECT c.id, c.name, c.description, uc.role
        FROM user_collaborations uc
        JOIN collaborations c ON uc.collaboration_id = c.id
        WHERE uc.user_id = :user_id;
        """
        collaborations = db.session.execute(query, {'user_id': user_id}).fetchall()

        collaborations_data = [
            {
                'id': collab[0],
                'name': collab[1],
                'description': collab[2],
                'role': collab[3]  # Add the role column
            }
            for collab in collaborations
        ]
        return jsonify(collaborations_data), 200
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to fetch joined collaborations.'}), 500
