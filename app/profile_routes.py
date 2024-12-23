from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from werkzeug.utils import secure_filename
import os
from flask import send_from_directory


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

@profile_bp.route('/collections/<int:collection_id>/items', methods=['POST'])
@jwt_required()
def add_item_to_collection(collection_id):
    try:
        user_id = get_jwt_identity()
        print(f"[DEBUG] User ID: {user_id}, Collection ID: {collection_id}")

        # Check if the request contains a file
        if 'file' in request.files:
            # Handle file uploads
            file = request.files.get('file')
            item_type = request.form.get('type')
            content = request.form.get('content')
            print(f"[DEBUG] Form data (file upload): Type: {item_type}, Content: {content}, File: {file.filename if file else 'None'}")

            if file:
                filename = secure_filename(file.filename)
                file_path = filename  # Only store the filename, not the full relative path
                print(f"[DEBUG] Preparing to save file at: {file_path}")
                file.save(file_path)
                print(f"[DEBUG] File saved at: {os.path.abspath(file_path)}")
            else:
                file_path = None
        else:
            # Handle JSON payloads
            data = request.get_json()
            item_type = data.get('type')
            content = data.get('content')
            file_path = None  # No file for text-based items
            print(f"[DEBUG] JSON data: Type: {item_type}, Content: {content}")

        # Ensure mandatory fields are present
        if not item_type or not content:
            print("[ERROR] Missing type or content in request")
            return jsonify({'error': 'Type and content are required fields'}), 400

        # Insert into database
        query = """
        INSERT INTO collection_items (collection_id, type, content, file_path)
        VALUES (:collection_id, :type, :content, :file_path)
        """
        db.session.execute(query, {
            'collection_id': collection_id,
            'type': item_type,
            'content': content,
            'file_path': file_path
        })
        db.session.commit()

        print(f"[DEBUG] Item added to database - Type: {item_type}, Content: {content}, File Path: {file_path}")
        return jsonify({'message': 'Item added to collection successfully', 'file_path': file_path}), 201
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': str(e)}), 500


@profile_bp.route('/collections', methods=['GET'])
@jwt_required()
def get_collections():
    user_id = get_jwt_identity()
    print(f"[DEBUG] Fetching collections for user_id: {user_id}")

    query = "SELECT id, name FROM collections WHERE user_id = :user_id"
    collections = db.session.execute(query, {'user_id': user_id}).fetchall()

    collections_data = [{'id': col[0], 'name': col[1]} for col in collections]
    print(f"[DEBUG] Retrieved collections: {collections_data}")
    return jsonify(collections_data), 200


@profile_bp.route('/collections/<int:collection_id>', methods=['GET'])
@jwt_required()
def get_collection_items(collection_id):
    try:
        print(f"[DEBUG] Fetching items for Collection ID: {collection_id}")

        query = """
        SELECT id, type, content, file_path FROM collection_items WHERE collection_id = :collection_id
        """
        items = db.session.execute(query, {'collection_id': collection_id}).fetchall()
        print(f"[DEBUG] Raw items from database: {items}")

        items_data = []
        for item in items:
            normalized_file_path = (
                f"http://127.0.0.1:5000/uploads/{item[3]}" if item[3] else None
            )
            print(f"[DEBUG] Normalizing file path: {item[3]} -> {normalized_file_path}")

            items_data.append({
                'id': item[0],
                'type': item[1],
                'content': item[2],
                'file_path': normalized_file_path
            })

        print(f"[DEBUG] Items data prepared for response: {items_data}")
        return jsonify(items_data), 200
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': str(e)}), 500



@profile_bp.route('/collections/<int:collection_id>', methods=['DELETE'])
@jwt_required()
def delete_collection(collection_id):
    print(f"[DEBUG] Deleting collection_id: {collection_id}")

    query = "DELETE FROM collections WHERE id = :collection_id"
    db.session.execute(query, {'collection_id': collection_id})
    db.session.commit()

    print(f"[DEBUG] Collection deleted: {collection_id}")
    return jsonify({'message': 'Collection deleted successfully'}), 200


@profile_bp.route('/collections/<int:collection_id>/items/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(collection_id, item_id):
    print(f"[DEBUG] Deleting item_id: {item_id} from collection_id: {collection_id}")

    query = """
    DELETE FROM collection_items WHERE collection_id = :collection_id AND id = :item_id
    """
    db.session.execute(query, {'collection_id': collection_id, 'item_id': item_id})
    db.session.commit()

    print(f"[DEBUG] Item deleted: {item_id} from collection_id: {collection_id}")
    return jsonify({'message': 'Item deleted successfully'}), 200


@profile_bp.route('/uploads/<path:filename>', methods=['GET'])
def serve_upload(filename):
    try:
        upload_folder = os.path.join(os.getcwd(), 'uploads')
        file_path = os.path.join(upload_folder, filename)
        print(f"[DEBUG] File request: {filename}, Full path: {file_path}")

        if not os.path.exists(file_path):
            print(f"[ERROR] File not found at: {file_path}")
            return jsonify({'error': 'File not found'}), 404

        print(f"[DEBUG] File exists. Serving: {filename}")
        return send_from_directory(upload_folder, filename)
    except Exception as e:
        print(f"[ERROR] Failed to serve file: {filename}. Error: {e}")
        return jsonify({'error': 'File not found or inaccessible'}), 404
