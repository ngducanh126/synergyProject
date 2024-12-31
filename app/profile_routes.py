from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from werkzeug.utils import secure_filename
import os
from flask import send_from_directory
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


profile_bp = Blueprint('profile', __name__)


# view my profile
@profile_bp.route('/view', methods=['GET'])
@jwt_required()
def view_profile():
    user_id = get_jwt_identity()

    try:
        # Fetch current user details
        user_query = """
        SELECT id, username, bio, skills, location, availability, verification_status, profile_picture
        FROM users
        WHERE id = :user_id;
        """
        user = db.session.execute(user_query, {'user_id': user_id}).fetchone()

        if not user:
            print(f"[DEBUG] User with ID {user_id} not found.")
            return jsonify({'message': 'User not found'}), 404

        print(f"[DEBUG] Retrieved user: ID={user[0]}, Username={user[1]}, Profile Picture={user[7]}")

        # Fetch collaborations where the user is a member or admin
        collaborations_query = """
        SELECT c.id, c.name, c.description, 
               CASE 
                   WHEN c.admin_id = :user_id THEN 'admin'
                   ELSE 'member'
               END AS role
        FROM collaborations c
        LEFT JOIN user_collaborations uc ON c.id = uc.collaboration_id AND uc.user_id = :user_id
        WHERE c.admin_id = :user_id OR uc.user_id = :user_id;
        """
        collaborations = db.session.execute(collaborations_query, {'user_id': user_id}).fetchall()

        collaborations_data = []
        for collab in collaborations:
            print(f"[DEBUG] Collaboration: ID={collab[0]}, Name={collab[1]}, Role={collab[3]}")
            collaborations_data.append({
                'id': collab[0],
                'name': collab[1],
                'description': collab[2],
                'role': collab[3]  # Add the role field (admin/member)
            })

        user_data = {
            'id': user[0],
            'username': user[1],
            'bio': user[2],
            'skills': user[3],
            'location': user[4],
            'availability': user[5],
            'verification_status': user[6],
            'profile_picture': user[7],  # Include profile_picture in the response
            'collaborations': collaborations_data,  # Add collaborations to the response
        }

        print("[DEBUG] Final user data response:")
        print(user_data)

        return jsonify(user_data), 200

    except Exception as e:
        print(f"[ERROR] Failed to fetch profile: {e}")
        return jsonify({'message': 'Failed to fetch profile'}), 500


# update my profile
@profile_bp.route('/update', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()

    # Check if the user exists
    user_query = "SELECT id FROM users WHERE id = :user_id;"
    user = db.session.execute(user_query, {'user_id': user_id}).fetchone()

    if not user:
        return jsonify({'message': 'User not found'}), 404

    # Initialize variables
    bio = request.form.get('bio')
    skills = request.form.get('skills')  # Assume this is a comma-separated string
    location = request.form.get('location')
    availability = request.form.get('availability')
    file = request.files.get('profile_picture')

    # Handle profile picture upload
    profile_picture_path = None
    if file:
        try:
            upload_folder = os.path.join(os.getcwd(), 'uploads', 'profile_picture')
            os.makedirs(upload_folder, exist_ok=True)  # Ensure the directory exists

            # Generate a secure filename
            filename = secure_filename(f"user_{user_id}_{file.filename}")
            file_path = os.path.join(upload_folder, filename)
            
            # Save the file to the directory
            file.save(file_path)
            profile_picture_path = f"uploads/profile_picture/{filename}"
        except Exception as e:
            print(f"[ERROR] Failed to save profile picture: {e}")
            return jsonify({'message': 'Failed to save profile picture', 'error': str(e)}), 500

    # Convert skills to PostgreSQL array format
    if skills:
        skills = "{" + ",".join(skill.strip() for skill in skills.split(',')) + "}"

    # Update profile data in the database
    update_query = """
    UPDATE users
    SET bio = COALESCE(:bio, bio),
        skills = COALESCE(:skills, skills),
        location = COALESCE(:location, location),
        availability = COALESCE(:availability, availability),
        profile_picture = COALESCE(:profile_picture, profile_picture)
    WHERE id = :user_id;
    """
    try:
        db.session.execute(
            update_query,
            {
                'bio': bio,
                'skills': skills,
                'location': location,
                'availability': availability,
                'profile_picture': profile_picture_path,
                'user_id': user_id,
            },
        )
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully'}), 200
    except Exception as e:
        print(f"[ERROR] Failed to update profile: {e}")
        return jsonify({'message': 'Failed to update profile', 'error': str(e)}), 500


# Fetch other users' profiles
@profile_bp.route('/get_others', methods=['GET'])
@jwt_required()
def get_other_users():
    """
    Fetch all other users except the current user, optionally filtered by collaboration ID.
    """
    current_user_id = get_jwt_identity()
    collaboration_id = request.args.get('collaboration_id', type=int)  # Optional filter

    try:
        if collaboration_id:
            # Fetch other users in the specified collaboration
            query = """
            SELECT u.id, u.username, u.bio, u.skills, u.location, u.profile_picture
            FROM users u
            JOIN user_collaborations uc ON u.id = uc.user_id
            WHERE uc.collaboration_id = :collaboration_id AND u.id != :current_user_id;
            """
            params = {'collaboration_id': collaboration_id, 'current_user_id': current_user_id}
        else:
            # Fetch all other users except the current user
            query = """
            SELECT id, username, bio, skills, location, profile_picture
            FROM users
            WHERE id != :current_user_id;
            """
            params = {'current_user_id': current_user_id}

        other_users = db.session.execute(query, params).fetchall()

        if not other_users:
            print(f"[DEBUG] No other users found for user ID {current_user_id}.")
            return jsonify({'message': 'No other users available'}), 404

        # Format the response data
        users_data = [
            {
                'id': user[0],
                'username': user[1],
                'bio': user[2],
                'skills': user[3],
                'location': user[4],
                'profile_picture': user[5],
            }
            for user in other_users
        ]

        print(f"[DEBUG] Retrieved {len(users_data)} other users for user ID {current_user_id}.")
        return jsonify(users_data), 200

    except Exception as e:
        print(f"[ERROR] Failed to fetch other users: {e}")
        return jsonify({'message': 'Failed to fetch other users'}), 500
    

# create a collection for current user ( name, descriotion, profile picture for collection)
@profile_bp.route('/collections', methods=['POST'])
@jwt_required()
def create_collection():
    user_id = get_jwt_identity()  # Get the current logged-in user's ID

    # Check if the collection name is provided in the request body
    data = request.get_json()
    collection_name = data.get('name')

    if not collection_name:
        return jsonify({'message': 'Collection name is required'}), 400

    try:
        # Insert the new collection into the collections table
        query = """
        INSERT INTO collections (user_id, name)
        VALUES (:user_id, :name)
        RETURNING id;
        """
        result = db.session.execute(query, {'user_id': user_id, 'name': collection_name})
        db.session.commit()

        # Get the ID of the newly created collection
        collection_id = result.fetchone()[0]

        return jsonify({'id': collection_id, 'name': collection_name}), 201

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to create collection'}), 500

# POST an item to one of my collection
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
                file_path = os.path.join('uploads', filename)  # Store relative path
                print(f"[DEBUG] Preparing to save file at: {file_path}")
                full_save_path = os.path.join(os.getcwd(), file_path)
                file.save(full_save_path)
                print(f"[DEBUG] File saved at: {full_save_path}")
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
            'file_path': file_path  # Store relative path only
        })
        db.session.commit()

        print(f"[DEBUG] Item added to database - Type: {item_type}, Content: {content}, File Path: {file_path}")
        return jsonify({'message': 'Item added to collection successfully', 'file_path': file_path}), 201
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': str(e)}), 500

# getting my collections
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

# getting collections for another user
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
            # Ensure the file path is normalized
            if item[3]:  # Check if file_path exists
                normalized_file_path = f"http://127.0.0.1:5000/{item[3]}"  # Prefix with base URL
            else:
                normalized_file_path = None

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

# delete one of my collections
@profile_bp.route('/collections/<int:collection_id>', methods=['DELETE'])
@jwt_required()
def delete_collection(collection_id):
    print(f"[DEBUG] Deleting collection_id: {collection_id}")

    query = "DELETE FROM collections WHERE id = :collection_id"
    db.session.execute(query, {'collection_id': collection_id})
    db.session.commit()

    print(f"[DEBUG] Collection deleted: {collection_id}")
    return jsonify({'message': 'Collection deleted successfully'}), 200


# delete an item from one of my collection
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

# getting collections for another user
@profile_bp.route('/<int:user_id>/collections', methods=['OPTIONS', 'GET'])
@jwt_required()
def get_collections_by_user(user_id):
    if request.method == 'OPTIONS':
        return '', 204  # Return HTTP 204 No Content for preflight
    # Handle GET request as usual
    try:
        print('getting collections for user id = ', user_id)
        query = "SELECT id, name FROM collections WHERE user_id = :user_id"
        collections = db.session.execute(query, {'user_id': user_id}).fetchall()
        collections_data = [{'id': col[0], 'name': col[1]} for col in collections]
        return jsonify(collections_data), 200
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to fetch collections for the user.'}), 500
    